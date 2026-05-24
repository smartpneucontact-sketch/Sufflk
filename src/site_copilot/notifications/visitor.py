"""Fire-and-forget visitor notification via Gmail SMTP.

When someone hits the landing page, look up their IP via the free ipapi.co
endpoint (city, region, country, org) and email the author. Best-effort:
never blocks the request, never raises into the request path."""

from __future__ import annotations

import asyncio
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Any

import httpx

# Dedup window so a single visitor refreshing doesn't spam.
_DEDUP_TTL_SEC = 24 * 3600
_seen_ips: dict[str, float] = {}

_BOT_SUBSTRINGS = (
    "bot", "crawler", "spider", "facebookexternalhit", "curl/",
    "python-requests", "axios/", "wget/", "go-http-client", "okhttp",
    "headlesschrome", "lighthouse", "uptime", "pingdom", "monitor",
)


def _is_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        return True
    return any(s in ua for s in _BOT_SUBSTRINGS)


def _is_private_or_loopback(ip: str) -> bool:
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return True
    if ":" in ip:  # IPv6 — skip private-range parsing, treat as public
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return True
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return True
    if a == 10 or a == 127:
        return True
    if a == 192 and b == 168:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 169 and b == 254:  # link-local
        return True
    return False


def _extract_ip(request: Any) -> str:
    # Railway/most PaaS put a proxy in front; the real client IP is in
    # X-Forwarded-For (leftmost entry). Fall back to direct peer.
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    return request.client.host if request.client else ""


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


def _send_email_sync(subject: str, body: str) -> None:
    user = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    to_addr = os.environ.get("NOTIFY_TO_EMAIL", user)
    if not (user and pw and to_addr):
        print("[site-copilot] visitor email skipped: GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set", flush=True)
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(user, pw)
            s.send_message(msg)
        print(f"[site-copilot] visitor email sent to {to_addr}: {subject}", flush=True)
    except Exception as e:
        print(f"[site-copilot] visitor email failed: {e}", flush=True)


async def _notify(ip: str, user_agent: str, path: str, referer: str) -> None:
    info = await _lookup_ip(ip)
    org = info.get("org") or info.get("asn") or ""
    city = info.get("city") or ""
    region = info.get("region") or info.get("region_code") or ""
    country = info.get("country_name") or info.get("country") or ""
    location = ", ".join(p for p in (city, region, country) if p) or "unknown"

    label = org or location or ip
    subject = f"Site Copilot visit: {label}"
    body = (
        "A visitor opened the Site Copilot demo.\n\n"
        f"Path:      {path}\n"
        f"IP:        {ip}\n"
        f"Location:  {location}\n"
        f"Org:       {org or 'unknown'}\n"
        f"Referer:   {referer or '(direct)'}\n"
        f"UA:        {user_agent or 'unknown'}\n"
    )
    await asyncio.to_thread(_send_email_sync, subject, body)


async def maybe_notify_visitor(request: Any, path: str) -> None:
    """Schedule a notification if this visit deserves one. Never blocks."""
    if os.environ.get("VISITOR_NOTIFY_ENABLED", "1") != "1":
        return
    ip = _extract_ip(request)
    if _is_private_or_loopback(ip):
        return
    ua = request.headers.get("user-agent", "")
    if _is_bot(ua):
        return
    now = time.time()
    last = _seen_ips.get(ip, 0)
    if now - last < _DEDUP_TTL_SEC:
        return
    _seen_ips[ip] = now
    # Opportunistic cleanup so the dict doesn't grow unbounded.
    if len(_seen_ips) > 2000:
        cutoff = now - _DEDUP_TTL_SEC
        for k in [k for k, v in _seen_ips.items() if v < cutoff]:
            _seen_ips.pop(k, None)

    referer = request.headers.get("referer", "")
    asyncio.create_task(_notify(ip, ua, path, referer))
