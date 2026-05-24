(() => {
  const $ = (id) => document.getElementById(id);
  const escape = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // === Tabs ===
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${target}`));
    });
  });

  // === Smooth scroll for in-page anchors ===
  document.querySelectorAll("[data-scroll]").forEach((a) => {
    a.addEventListener("click", (e) => {
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("#")) return;
      const el = document.querySelector(href);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  // === Health / mode ===
  fetch("/healthz")
    .then((r) => r.json())
    .then((h) => {
      const pill = $("mode-pill");
      const isLive = !h.use_mock_llm;
      pill.classList.add(isLive ? "live" : "mock");
      $("mode-text").textContent = isLive ? `LIVE · ${h.model}` : `MOCK · ${h.model}`;
      $("footer-mode").textContent = isLive ? `LIVE (${h.model})` : `MOCK (${h.model})`;
      $("stat-corpus").textContent = h.corpus_chunks ?? "—";
      $("stat-model").textContent = h.model;
      $("stat-retriever").textContent = h.retriever;
    })
    .catch(() => {
      $("mode-pill").classList.add("mock");
      $("mode-text").textContent = "offline";
    });

  // === Samples ===
  let rfiSamples = [];
  let dcrSamples = [];

  fetch("/api/samples/rfi").then((r) => r.json()).then((data) => {
    rfiSamples = data;
    const sel = $("rfi-sample");
    data.forEach((s, i) => {
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = `${s.rfi_id} — ${s.discipline}`;
      sel.appendChild(opt);
    });
    loadRfi(0);
  });

  fetch("/api/samples/dcr").then((r) => r.json()).then((data) => {
    dcrSamples = data;
    const sel = $("dcr-sample");
    data.forEach((s, i) => {
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = `${s.date} — ${s.author}`;
      sel.appendChild(opt);
    });
    loadDcr(0);
  });

  const loadRfi = (i) => {
    const s = rfiSamples[i];
    if (!s) return;
    $("rfi-id").value = s.rfi_id || "";
    $("rfi-discipline").value = s.discipline || "";
    $("rfi-trade").value = s.trade || "";
    $("rfi-refs").value = (s.references || []).join(", ");
    $("rfi-question").value = s.question || "";
  };
  $("rfi-sample").addEventListener("change", (e) => loadRfi(+e.target.value));

  const loadDcr = (i) => {
    const s = dcrSamples[i];
    if (!s) return;
    $("dcr-date").value = s.date || "";
    $("dcr-author").value = s.author || "";
    $("dcr-notes").value = s.raw_notes || "";
  };
  $("dcr-sample").addEventListener("change", (e) => loadDcr(+e.target.value));

  // === Submit helpers ===
  const setSubmitting = (btn, on) => {
    btn.disabled = on;
    btn.querySelector(".btn-text").textContent = on
      ? "Running…"
      : btn.dataset.label || btn.querySelector(".btn-text").textContent;
    btn.querySelector(".btn-spinner").hidden = !on;
  };

  const showStatus = (el, kind, msg) => {
    if (!msg) {
      el.hidden = true;
      el.className = "status";
      return;
    }
    el.hidden = false;
    el.className = `status ${kind}`;
    el.textContent = msg;
  };

  // Stash original button label text on first use so we can restore it.
  document.querySelectorAll(".btn-primary").forEach((b) => {
    const t = b.querySelector(".btn-text");
    if (t && !b.dataset.label) b.dataset.label = t.textContent;
  });

  // === RFI submit ===
  $("rfi-submit").addEventListener("click", async () => {
    const btn = $("rfi-submit");
    const status = $("rfi-status");
    const empty = $("rfi-empty");
    const result = $("rfi-result");

    const payload = {
      rfi_id: $("rfi-id").value.trim() || "RFI-DEMO",
      discipline: $("rfi-discipline").value.trim(),
      trade: $("rfi-trade").value.trim(),
      references: $("rfi-refs").value.split(",").map((s) => s.trim()).filter(Boolean),
      question: $("rfi-question").value.trim(),
    };

    setSubmitting(btn, true);
    showStatus(status, "running", "Retrieving from corpus and drafting response…");
    empty.hidden = true;
    result.hidden = false;
    result.innerHTML = renderRunningSkeleton();
    const t0 = performance.now();

    try {
      const resp = await fetch("/agents/rfi/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(await formatError(resp));
      const data = await resp.json();
      const wall = Math.round(performance.now() - t0);
      result.innerHTML = renderRfiResult(data, wall);
      showStatus(status, "ok", `Done — run_id ${data.run_id}`);
    } catch (e) {
      result.innerHTML = "";
      empty.hidden = false;
      showStatus(status, "error", e.message);
    } finally {
      setSubmitting(btn, false);
    }
  });

  // === DCR submit ===
  $("dcr-submit").addEventListener("click", async () => {
    const btn = $("dcr-submit");
    const status = $("dcr-status");
    const empty = $("dcr-empty");
    const result = $("dcr-result");

    const payload = {
      date: $("dcr-date").value.trim(),
      author: $("dcr-author").value.trim(),
      raw_notes: $("dcr-notes").value.trim(),
    };

    setSubmitting(btn, true);
    showStatus(status, "running", "Drafting structured DCR…");
    empty.hidden = true;
    result.hidden = false;
    result.innerHTML = renderRunningSkeleton();
    const t0 = performance.now();

    try {
      const resp = await fetch("/agents/daily-report/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(await formatError(resp));
      const data = await resp.json();
      const wall = Math.round(performance.now() - t0);
      result.innerHTML = renderDcrResult(data, wall);
      showStatus(status, "ok", `Done — run_id ${data.run_id}`);
    } catch (e) {
      result.innerHTML = "";
      empty.hidden = false;
      showStatus(status, "error", e.message);
    } finally {
      setSubmitting(btn, false);
    }
  });

  // === Error formatting ===
  async function formatError(resp) {
    let msg = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body && body.detail) {
        if (typeof body.detail === "string") {
          msg = `${msg}: ${body.detail}`;
        } else {
          const err = body.detail.error || "Error";
          const detail = body.detail.message || JSON.stringify(body.detail);
          msg = `${err}: ${detail}`;
        }
      }
    } catch (_) {}
    return msg;
  }

  // === Renderers ===
  const renderRunningSkeleton = () => `
    <div class="telemetry-strip">
      ${["Run", "Steps", "Tokens", "Cost"].map((l) => `
        <div class="telem-cell">
          <div class="telem-label">${l}</div>
          <div class="telem-value">…</div>
        </div>`).join("")}
    </div>
    <div class="empty-state" style="padding:50px 20px">
      <p class="muted">Agent is thinking — typically 8–15 seconds with tool calls.</p>
    </div>
  `;

  const telemetryStrip = (data, wallMs) => {
    const cost = (data.cost_usd ?? 0).toFixed(4);
    return `
      <div class="telemetry-strip">
        <div class="telem-cell">
          <div class="telem-label">Steps</div>
          <div class="telem-value">${data.steps ?? 0}</div>
        </div>
        <div class="telem-cell">
          <div class="telem-label">Tokens</div>
          <div class="telem-value">${(data.input_tokens || 0).toLocaleString()} <span class="muted" style="font-size:11px">in</span> · ${(data.output_tokens || 0).toLocaleString()} <span class="muted" style="font-size:11px">out</span></div>
        </div>
        <div class="telem-cell">
          <div class="telem-label">Cost</div>
          <div class="telem-value">$${cost}</div>
        </div>
        <div class="telem-cell">
          <div class="telem-label">Wall time</div>
          <div class="telem-value">${(wallMs / 1000).toFixed(1)}s</div>
        </div>
      </div>
    `;
  };

  const renderRfiResult = (data, wallMs) => {
    const parsed = data.parsed || {};
    const parts = [telemetryStrip(data, wallMs)];

    if (parsed.draft_response) {
      parts.push(`
        <div class="result-section">
          <h4 class="result-section-title">Draft response to subcontractor</h4>
          <div class="draft-card">${escape(parsed.draft_response)}</div>
          ${renderBadges(parsed)}
        </div>
      `);
    } else if (data.final_text) {
      parts.push(`
        <div class="result-section">
          <h4 class="result-section-title">Agent response (unparsed)</h4>
          <div class="draft-card">${escape(data.final_text)}</div>
        </div>
      `);
    }

    if (parsed.citations && parsed.citations.length) {
      parts.push(`
        <div class="result-section">
          <h4 class="result-section-title">Citations · ${parsed.citations.length}</h4>
          <div class="citations">
            ${parsed.citations.map(renderCitation).join("")}
          </div>
        </div>
      `);
    }

    if (parsed.rationale) {
      parts.push(`
        <div class="result-section">
          <h4 class="result-section-title">Reviewer rationale</h4>
          <div class="rationale">${escape(parsed.rationale)}</div>
        </div>
      `);
    }

    if (data.tool_invocations && data.tool_invocations.length) {
      parts.push(renderTimeline(data.tool_invocations));
    }

    return parts.join("");
  };

  const renderBadges = (p) => {
    const urgency = (p.urgency || "").toLowerCase();
    const eor = p.needs_eor_review ? "yes" : "no";
    const schedule = p.schedule_impact_days != null ? `${p.schedule_impact_days} d` : "—";
    const cost = p.cost_impact_usd_estimate != null ? `$${Number(p.cost_impact_usd_estimate).toLocaleString()}` : "—";
    return `
      <div class="badges">
        <span class="badge urgency-${urgency}"><span class="b-label">urgency</span><span class="b-value">${escape(p.urgency || "—")}</span></span>
        <span class="badge flag-${p.needs_eor_review ? "yes" : "no"}"><span class="b-label">EOR review</span><span class="b-value">${eor}</span></span>
        <span class="badge"><span class="b-label">schedule impact</span><span class="b-value">${schedule}</span></span>
        <span class="badge"><span class="b-label">cost impact</span><span class="b-value">${cost}</span></span>
      </div>
    `;
  };

  const renderCitation = (c) => {
    const src = c.source || "";
    const [type, ...rest] = src.split(":");
    const id = rest.join(":");
    return `
      <div class="citation">
        <span class="citation-type ${escape(type)}">${escape(type || "ref")}</span>
        <div class="citation-body">
          <div class="citation-source">${escape(id || src)}</div>
          ${c.section ? `<div class="citation-section">§ ${escape(c.section)}</div>` : ""}
          ${c.note ? `<div class="citation-note">${escape(c.note)}</div>` : ""}
        </div>
      </div>
    `;
  };

  const renderTimeline = (invocations) => {
    const steps = invocations.map((inv, i) => `
      <div class="tool-step">
        <div class="tool-dot">${i + 1}</div>
        <details class="tool-card" ${i === 0 ? "open" : ""}>
          <summary>
            <span class="tool-name">${escape(inv.name)}</span>
            <span class="tool-args">${escape(formatToolArgs(inv.input))}</span>
          </summary>
          <div class="tool-body">${renderToolResult(inv)}</div>
        </details>
      </div>
    `).join("");
    return `
      <div class="result-section">
        <h4 class="result-section-title">Agent reasoning · ${invocations.length} tool calls</h4>
        <div class="timeline">${steps}</div>
      </div>
    `;
  };

  const formatToolArgs = (obj) => {
    if (!obj || typeof obj !== "object") return "";
    return Object.entries(obj)
      .map(([k, v]) => {
        const sv = typeof v === "string" && v.length > 50 ? v.slice(0, 50) + "…" : JSON.stringify(v);
        return `${k}=${sv}`;
      })
      .join(", ");
  };

  const renderToolResult = (inv) => {
    const r = inv.result;
    if (r && Array.isArray(r.results)) {
      const items = r.results.slice(0, 8).map((x) => `
        <li>
          <span class="ret-id">${escape(x.source_type)}:${escape(x.source_id)}${x.section ? " · " + escape(x.section) : ""}</span>
          <span class="ret-score">${x.score}</span>
        </li>
      `).join("");
      return `<div class="muted" style="margin-top:10px;font-size:12px">${r.count} chunks returned</div><ul class="retrieved-list">${items}</ul>`;
    }
    return `<pre>${escape(JSON.stringify(r, null, 2))}</pre>`;
  };

  // === DCR renderer ===
  const renderDcrResult = (data, wallMs) => {
    const p = data.parsed || {};
    const parts = [telemetryStrip(data, wallMs)];

    if (p.summary) {
      parts.push(`
        <div class="result-section">
          <h4 class="result-section-title">Executive summary</h4>
          <div class="dcr-summary">${escape(p.summary)}</div>
        </div>
      `);
    } else if (data.final_text && !Object.keys(p).length) {
      parts.push(`<div class="result-section"><h4 class="result-section-title">Raw output</h4><div class="draft-card">${escape(data.final_text)}</div></div>`);
    }

    if (p.weather || p.crews_on_site) {
      const cells = [];
      if (p.date) cells.push(["date", p.date]);
      if (p.author) cells.push(["author", p.author]);
      if (p.weather && typeof p.weather === "object") {
        const w = p.weather;
        if (w.am_temp_f != null) cells.push(["AM temp °F", w.am_temp_f]);
        if (w.pm_temp_f != null) cells.push(["PM temp °F", w.pm_temp_f]);
        if (w.precip_in != null) cells.push(["precip (in)", w.precip_in]);
      }
      if (p.crews_on_site && typeof p.crews_on_site === "object") {
        const total = Object.values(p.crews_on_site).reduce((a, b) => a + (Number(b) || 0), 0);
        cells.push(["total on site", total]);
      }
      if (cells.length) {
        parts.push(`
          <div class="result-section">
            <h4 class="result-section-title">Conditions</h4>
            <div class="kv-grid">${cells.map(([k, v]) => `<div class="kv"><div class="kv-k">${escape(k)}</div><div class="kv-v">${escape(v)}</div></div>`).join("")}</div>
          </div>
        `);
      }
    }

    if (p.crews_on_site && typeof p.crews_on_site === "object") {
      const items = Object.entries(p.crews_on_site).map(([k, v]) => `<li>${escape(k)}: <strong>${escape(v)}</strong></li>`).join("");
      parts.push(`<div class="result-section"><h4 class="result-section-title">Crews</h4><ul class="list-tight">${items}</ul></div>`);
    }

    if (Array.isArray(p.areas_worked) && p.areas_worked.length) {
      parts.push(`<div class="result-section"><h4 class="result-section-title">Areas worked</h4><ul class="list-tight">${p.areas_worked.map((s) => `<li>${escape(s)}</li>`).join("")}</ul></div>`);
    }
    if (Array.isArray(p.equipment) && p.equipment.length) {
      parts.push(`<div class="result-section"><h4 class="result-section-title">Equipment</h4><ul class="list-tight">${p.equipment.map((s) => `<li>${escape(s)}</li>`).join("")}</ul></div>`);
    }
    if (Array.isArray(p.deliveries) && p.deliveries.length) {
      parts.push(`<div class="result-section"><h4 class="result-section-title">Deliveries</h4><ul class="list-tight">${p.deliveries.map((s) => `<li>${escape(s)}</li>`).join("")}</ul></div>`);
    }
    if (Array.isArray(p.risks) && p.risks.length) {
      const items = p.risks.map((r) => `
        <div class="risk">
          <span class="risk-cat ${escape((r.category || "").toLowerCase())}">${escape(r.category || "—")}</span>
          <div class="risk-note">${escape(r.note || "")}</div>
        </div>
      `).join("");
      parts.push(`<div class="result-section"><h4 class="result-section-title">Risks · ${p.risks.length}</h4><div class="risks">${items}</div></div>`);
    }
    if (Array.isArray(p.open_rfis) && p.open_rfis.length) {
      parts.push(`<div class="result-section"><h4 class="result-section-title">Open RFIs</h4><ul class="list-tight">${p.open_rfis.map((s) => `<li>${escape(s)}</li>`).join("")}</ul></div>`);
    }
    if (Array.isArray(p.follow_ups) && p.follow_ups.length) {
      parts.push(`<div class="result-section"><h4 class="result-section-title">Follow-ups for tomorrow</h4><ul class="list-tight">${p.follow_ups.map((s) => `<li>${escape(s)}</li>`).join("")}</ul></div>`);
    }

    if (data.tool_invocations && data.tool_invocations.length) {
      parts.push(renderTimeline(data.tool_invocations));
    }
    return parts.join("");
  };
})();
