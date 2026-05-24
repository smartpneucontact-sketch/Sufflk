(() => {
  const $ = (id) => document.getElementById(id);

  // --- Tab switching ---
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      document.querySelectorAll(".panel").forEach((p) => {
        p.classList.toggle("active", p.id === `tab-${target}`);
      });
    });
  });

  // --- Mode badge from /healthz ---
  fetch("/healthz")
    .then((r) => r.json())
    .then((h) => {
      const badge = $("mode-badge");
      const isLive = !h.use_mock_llm;
      badge.textContent = isLive ? `LIVE · ${h.model}` : `MOCK · ${h.model}`;
      badge.classList.add(isLive ? "live" : "mock");
      $("footer-mode").textContent = isLive ? `LIVE (${h.model})` : `MOCK (${h.model})`;
    })
    .catch(() => {
      $("mode-badge").textContent = "offline";
      $("mode-badge").classList.add("mock");
    });

  // --- Sample loaders ---
  let rfiSamples = [];
  let dcrSamples = [];

  fetch("/api/samples/rfi")
    .then((r) => r.json())
    .then((data) => {
      rfiSamples = data;
      const sel = $("rfi-sample");
      data.forEach((s, i) => {
        const opt = document.createElement("option");
        opt.value = i;
        opt.textContent = `${s.rfi_id} — ${s.discipline}`;
        sel.appendChild(opt);
      });
      loadRfiSample(0);
    });

  fetch("/api/samples/dcr")
    .then((r) => r.json())
    .then((data) => {
      dcrSamples = data;
      const sel = $("dcr-sample");
      data.forEach((s, i) => {
        const opt = document.createElement("option");
        opt.value = i;
        opt.textContent = `${s.date} — ${s.author}`;
        sel.appendChild(opt);
      });
      loadDcrSample(0);
    });

  const loadRfiSample = (i) => {
    const s = rfiSamples[i];
    if (!s) return;
    $("rfi-id").value = s.rfi_id || "";
    $("rfi-discipline").value = s.discipline || "";
    $("rfi-trade").value = s.trade || "";
    $("rfi-refs").value = (s.references || []).join(", ");
    $("rfi-question").value = s.question || "";
  };
  $("rfi-sample").addEventListener("change", (e) => loadRfiSample(+e.target.value));

  const loadDcrSample = (i) => {
    const s = dcrSamples[i];
    if (!s) return;
    $("dcr-date").value = s.date || "";
    $("dcr-author").value = s.author || "";
    $("dcr-notes").value = s.raw_notes || "";
  };
  $("dcr-sample").addEventListener("change", (e) => loadDcrSample(+e.target.value));

  // --- RFI submit ---
  $("rfi-submit").addEventListener("click", async () => {
    const btn = $("rfi-submit");
    const status = $("rfi-status");
    const output = $("rfi-output");
    const telemetry = $("rfi-telemetry");

    const payload = {
      rfi_id: $("rfi-id").value.trim() || "RFI-DEMO",
      discipline: $("rfi-discipline").value.trim(),
      trade: $("rfi-trade").value.trim(),
      references: $("rfi-refs").value.split(",").map((s) => s.trim()).filter(Boolean),
      question: $("rfi-question").value.trim(),
    };

    btn.disabled = true;
    status.className = "status";
    status.textContent = "Retrieving and drafting…";
    output.innerHTML = '<p class="placeholder">Running agent…</p>';
    telemetry.textContent = "";
    const t0 = performance.now();

    try {
      const resp = await fetch("/agents/rfi/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const result = await resp.json();
      const wallMs = Math.round(performance.now() - t0);
      renderAgentResult(output, telemetry, result, wallMs);
      status.className = "status ok";
      status.textContent = `Done. run_id ${result.run_id}`;
    } catch (e) {
      status.className = "status error";
      status.textContent = `Error: ${e.message}`;
      output.innerHTML = '<p class="placeholder">Run failed — see status above.</p>';
    } finally {
      btn.disabled = false;
    }
  });

  // --- DCR submit ---
  $("dcr-submit").addEventListener("click", async () => {
    const btn = $("dcr-submit");
    const status = $("dcr-status");
    const output = $("dcr-output");
    const telemetry = $("dcr-telemetry");

    const payload = {
      date: $("dcr-date").value.trim(),
      author: $("dcr-author").value.trim(),
      raw_notes: $("dcr-notes").value.trim(),
    };

    btn.disabled = true;
    status.className = "status";
    status.textContent = "Drafting structured DCR…";
    output.innerHTML = '<p class="placeholder">Running agent…</p>';
    telemetry.textContent = "";
    const t0 = performance.now();

    try {
      const resp = await fetch("/agents/daily-report/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const result = await resp.json();
      const wallMs = Math.round(performance.now() - t0);
      renderAgentResult(output, telemetry, result, wallMs);
      status.className = "status ok";
      status.textContent = `Done. run_id ${result.run_id}`;
    } catch (e) {
      status.className = "status error";
      status.textContent = `Error: ${e.message}`;
      output.innerHTML = '<p class="placeholder">Run failed — see status above.</p>';
    } finally {
      btn.disabled = false;
    }
  });

  // --- Renderer ---
  const renderAgentResult = (outputEl, telemetryEl, result, wallMs) => {
    const cost = (result.cost_usd ?? 0).toFixed(5);
    telemetryEl.textContent = `${result.steps} steps · ${result.input_tokens}+${result.output_tokens} tok · $${cost} · ${wallMs}ms wall`;

    const sections = [];

    // Parsed JSON (the main payload)
    const parsed = result.parsed ?? null;
    if (parsed) {
      sections.push(`<span class="section-label">Agent response</span><pre class="codeblock">${escapeHtml(JSON.stringify(parsed, null, 2))}</pre>`);
    } else if (result.final_text) {
      sections.push(`<span class="section-label">Agent response (raw)</span><pre class="codeblock">${escapeHtml(result.final_text)}</pre>`);
    }

    // Tool invocations
    if (result.tool_invocations && result.tool_invocations.length) {
      const items = result.tool_invocations
        .map((inv) => renderToolInvocation(inv))
        .join("");
      sections.push(`<span class="section-label">Tool invocations (${result.tool_invocations.length})</span><ul class="tool-list">${items}</ul>`);
    }

    outputEl.innerHTML = sections.join("") || '<p class="placeholder">No content returned.</p>';
  };

  const renderToolInvocation = (inv) => {
    const label = `step ${inv.step} → ${inv.name}(${shortInput(inv.input)})`;
    let bodyHtml = "";
    if (inv.result && Array.isArray(inv.result.results)) {
      const items = inv.result.results
        .slice(0, 8)
        .map((r) => {
          const head = r.section || r.source_id || "";
          return `<li><code>${escapeHtml(r.source_type)}:${escapeHtml(r.source_id)}</code> ${head ? "— " + escapeHtml(head) : ""} <span class="muted">score ${r.score}</span></li>`;
        })
        .join("");
      bodyHtml = `<div class="muted" style="margin-bottom:6px">${inv.result.count} chunks returned</div><ul style="margin:0 0 0 16px;padding:0">${items}</ul>`;
    } else {
      bodyHtml = `<pre class="codeblock">${escapeHtml(JSON.stringify(inv.result, null, 2))}</pre>`;
    }
    return `<details class="tool-item"><summary class="tool-summary">${escapeHtml(label)}</summary><div class="tool-body">${bodyHtml}</div></details>`;
  };

  const shortInput = (obj) => {
    if (!obj || typeof obj !== "object") return "";
    const parts = Object.entries(obj).map(([k, v]) => {
      const sv = typeof v === "string" && v.length > 40 ? v.slice(0, 40) + "…" : JSON.stringify(v);
      return `${k}=${sv}`;
    });
    return parts.join(", ");
  };

  const escapeHtml = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
})();
