"""Fire-and-forget visitor notification.

Two transports supported — picks the first available, in this order:
  1. Resend HTTPS API (RESEND_API_KEY) — works on Railway / any PaaS
     because it's plain HTTPS.
  2. Gmail SMTP (GMAIL_ADDRESS + GMAIL_APP_PASSWORD) — blocked by most
     PaaS providers; kept as a fallback for local development.

When someone hits the landing page, look up their IP via the free
ipapi.co endpoint (city, region, country, org) and email the author.
Best-effort: never blocks the request, never raises into the request
path.
"""

from __future__ import annotations

import asyncio
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Any

import httpx

_DEDUP_TTL_SEC = 24 * 3600
_seen_ips: dict[str, float] = {}

_BOT_SUBSTRINGS = (
    "bot", "crawler", "spider", "facebookexternalhit", "curl/",
    "python-requests", "axios/", "wget/", "go-http-client", "okhttp",
    "headlesschrome", "lighthouse", "uptime", "pingdom", "monitor",
)

_DEFAULT_FROM = "Site Copilot <onboarding@resend.dev>"


# === Filters ===

def _is_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        return True
    return any(s in ua for s in _BOT_SUBSTRINGS)


def _is_private_or_loopback(ip: str) -> bool:
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return True
    if ":" in ip:
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return True
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return True
    if a in (10, 127):
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 169 and b == 254:
        return True
    return False


def _extract_ip(request: Any) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    return request.client.host if request.client else ""


# === Transport selection ===

def _has_resend() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def _has_gmail() -> bool:
    return bool(os.environ.get("GMAIL_ADDRESS")) and bool(os.environ.get("GMAIL_APP_PASSWORD"))


def _selected_transport() -> str:
    if _has_resend():
        return "resend"
    if _has_gmail():
        return "gmail_smtp"
    return "none"


def _recipient() -> str:
    return os.environ.get("NOTIFY_TO_EMAIL") or os.environ.get("GMAIL_ADDRESS") or ""


def _from_address() -> str:
    # Explicit override always wins.
    explicit = os.environ.get("NOTIFY_FROM_EMAIL")
    if explicit:
        return explicit
    # For Resend, default to its sandbox sender — using GMAIL_ADDRESS here
    # would be rejected because gmail.com isn't a domain the user has
    # verified through Resend.
    if _has_resend():
        return _DEFAULT_FROM
    # For Gmail SMTP, From must be the authenticated mailbox.
    return os.environ.get("GMAIL_ADDRESS") or _DEFAULT_FROM


# === Geo lookup ===

async def _lookup_ip(ip: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"https://ipapi.co/{ip}/json/")
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and not data.get("error"):
                    return data
    except Exception as e:
        print(f"[site-copilot] ipapi lookup failed for {ip}: {e}", flush=True)
    return {}


# === Send paths ===

async def _send_via_resend(subject: str, body: str) -> dict[str, Any]:
    api_key = os.environ.get("RESEND_API_KEY", "")
    to = _recipient()
    sender = _from_address()
    if not to:
        return {"ok": False, "error": "NOTIFY_TO_EMAIL not set (and no GMAIL_ADDRESS fallback)"}
    payload = {"from": sender, "to": [to], "subject": subject, "text": body}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if 200 <= r.status_code < 300:
            return {"ok": True, "transport": "resend", "id": r.json().get("id")}
        return {
            "ok": False,
            "transport": "resend",
            "error": f"HTTP {r.status_code}",
            "detail": r.text[:500],
        }
    except Exception as e:
        return {"ok": False, "transport": "resend", "error": type(e).__name__, "detail": str(e)}


def _send_via_gmail_sync(subject: str, body: str) -> dict[str, Any]:
    user = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    to = _recipient()
    if not (user and pw and to):
        return {"ok": False, "error": "GMAIL credentials or NOTIFY_TO_EMAIL not set"}
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(user, pw)
            s.send_message(msg)
        return {"ok": True, "transport": "gmail_smtp"}
    except Exception as e:
        return {"ok": False, "transport": "gmail_smtp", "error": type(e).__name__, "detail": str(e)}


async def _send(subject: str, body: str) -> dict[str, Any]:
    t = _selected_transport()
    if t == "resend":
        return await _send_via_resend(subject, body)
    if t == "gmail_smtp":
        return await asyncio.to_thread(_send_via_gmail_sync, subject, body)
    return {"ok": False, "error": "no transport configured (set RESEND_API_KEY or GMAIL_*)"}


# === Visitor pipeline ===

async def _notify(ip: str, user_agent: str, path: str, referer: str, host: str = "") -> None:
    info = await _lookup_ip(ip)
    org = info.get("org") or info.get("asn") or ""
    city = info.get("city") or ""
    region = info.get("region") or info.get("region_code") or ""
    country = info.get("country_name") or info.get("country") or ""
    location = ", ".join(p for p in (city, region, country) if p) or "unknown"

    label = org or location or ip
    full_url = f"https://{host}{path}" if host else path
    subject = f"[Site Copilot] visit from {label}"
    body = (
        "Site Copilot — Suffolk Construction demo · new visitor.\n\n"
        f"URL:       {full_url}\n"
        f"IP:        {ip}\n"
        f"Location:  {location}\n"
        f"Org:       {org or 'unknown'}\n"
        f"Referer:   {referer or '(direct)'}\n"
        f"UA:        {user_agent or 'unknown'}\n"
    )
    result = await _send(subject, body)
    if result.get("ok"):
        print(f"[site-copilot] visitor email sent via {result.get('transport')}: {subject}", flush=True)
    else:
        print(f"[site-copilot] visitor email failed: {result}", flush=True)


async def maybe_notify_visitor(request: Any, path: str) -> None:
    if os.environ.get("VISITOR_NOTIFY_ENABLED", "1") != "1":
        print("[site-copilot] visitor: skip (notify disabled by env)", flush=True)
        return
    ip = _extract_ip(request)
    if _is_private_or_loopback(ip):
        print(f"[site-copilot] visitor: skip (private/loopback ip={ip!r})", flush=True)
        return
    ua = request.headers.get("user-agent", "")
    if _is_bot(ua):
        print(f"[site-copilot] visitor: skip (bot ua={ua[:80]!r})", flush=True)
        return
    now = time.time()
    last = _seen_ips.get(ip, 0)
    if now - last < _DEDUP_TTL_SEC:
        remaining = int(_DEDUP_TTL_SEC - (now - last))
        print(f"[site-copilot] visitor: skip (dedup, ip={ip}, {remaining}s left)", flush=True)
        return
    _seen_ips[ip] = now
    if len(_seen_ips) > 2000:
        cutoff = now - _DEDUP_TTL_SEC
        for k in [k for k, v in _seen_ips.items() if v < cutoff]:
            _seen_ips.pop(k, None)
    referer = request.headers.get("referer", "")
    host = (
        request.headers.get("x-forwarded-host", "")
        or request.headers.get("host", "")
    )
    print(f"[site-copilot] visitor: queued notify for ip={ip} via {_selected_transport()}", flush=True)
    asyncio.create_task(_notify(ip, ua, path, referer, host))


# === Diagnostics ===

def diagnostic_status() -> dict[str, Any]:
    user = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    rk = os.environ.get("RESEND_API_KEY")
    to = _recipient()
    enabled = os.environ.get("VISITOR_NOTIFY_ENABLED", "1") == "1"

    masked_user = ""
    if user:
        local, _, domain = user.partition("@")
        if local and domain:
            masked_user = f"{local[:2]}***@{domain}"

    now = time.time()
    recent = sorted(
        ((ip, int(now - ts)) for ip, ts in _seen_ips.items()),
        key=lambda x: x[1],
    )[:10]
    masked_recent = []
    for ip, age in recent:
        if "." in ip:
            parts = ip.split(".")
            masked_recent.append({"ip": ".".join(parts[:3] + ["x"]), "seconds_ago": age})
        else:
            masked_recent.append({"ip": "(ipv6)", "seconds_ago": age})

    return {
        "enabled": enabled,
        "selected_transport": _selected_transport(),
        "resend_api_key_set": bool(rk),
        "resend_api_key_length": len(rk) if rk else 0,
        "gmail_address_set": bool(user),
        "gmail_app_password_set": bool(pw),
        "gmail_app_password_length": len(pw) if pw else 0,
        "notify_to_email_set": bool(os.environ.get("NOTIFY_TO_EMAIL")),
        "effective_from": _from_address(),
        "effective_to_email_domain": (to.partition("@")[2] if to else ""),
        "deduped_ip_count": len(_seen_ips),
        "recent_seen_ips_masked": masked_recent,
    }


async def smtp_login_check() -> dict[str, Any]:
    """Kept for backward-compat with the previous diagnostic. Now also
    works as a transport-aware liveness check."""
    t = _selected_transport()
    if t == "resend":
        # No equivalent 'login check' for Resend — the test send is the
        # real check. Return a hint instead.
        return {
            "ok": True,
            "transport": "resend",
            "note": "Resend is HTTPS — there's no separate auth step. POST /api/notify/test to actually verify.",
        }
    if t == "gmail_smtp":
        def _check() -> dict[str, Any]:
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as s:
                    s.login(os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"])
                return {"ok": True, "transport": "gmail_smtp"}
            except Exception as e:
                return {"ok": False, "transport": "gmail_smtp", "error": type(e).__name__, "detail": str(e)}
        return await asyncio.to_thread(_check)
    return {"ok": False, "error": "no transport configured"}


async def send_test_email() -> dict[str, Any]:
    subject = "Site Copilot — visitor-notify test"
    body = (
        "This is a test from the Site Copilot deploy.\n\n"
        f"Transport: {_selected_transport()}\n\n"
        "If you received this, notifications will fire on the next un-deduped page view."
    )
    return await _send(subject, body)
