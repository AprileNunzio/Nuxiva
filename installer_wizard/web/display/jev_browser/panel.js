(() => {
  const D = window.NuxivaDisplay;
  if (!D || !D.stagePanels) return;
  const { fmt } = D;
  const { render, wide } = D.stagePanels;
  const esc = fmt.esc;

  function inspectFirewall(rawUrl) {
    const clean = String(rawUrl || "").trim();
    if (!clean) {
      return { allowed: false, url: "", reason: "jev_fw_blocked" };
    }
    if (!/^https?:\/\//i.test(clean)) {
      if (/^(javascript|data|vbscript|file):/i.test(clean)) {
        return { allowed: false, url: "", reason: "jev_fw_blocked" };
      }
      return {
        allowed: true,
        url: `https://www.google.com/search?q=${encodeURIComponent(clean)}`,
        reason: "jev_fw_active",
      };
    }
    try {
      const parsed = new URL(clean);
      const h = (parsed.hostname || "").toLowerCase();
      if (
        !h ||
        h === "localhost" ||
        h.endsWith(".local") ||
        h.startsWith("127.") ||
        h.startsWith("10.") ||
        h.startsWith("192.168.") ||
        h.startsWith("169.254.") ||
        h === "0.0.0.0" ||
        h === "[::1]"
      ) {
        return { allowed: false, url: "", reason: "jev_fw_blocked" };
      }
      return { allowed: true, url: parsed.toString(), reason: "jev_fw_active" };
    } catch (_) {
      return { allowed: false, url: "", reason: "jev_fw_blocked" };
    }
  }

  render.jev_web = (p) => {
    const d = p.data || {};
    const fw = inspectFirewall(d.entry_url || d.url || "https://www.google.com");
    const steps = Array.isArray(d.steps) ? d.steps : [];
    const current = Number(d.current_step || 0);

    const stepsHtml = steps
      .map((s, idx) => {
        const cls = s.verified ? "done" : idx === current ? "active" : "";
        const phaseKey = `jev_phase_${s.phase || "judge"}`;
        return `<div class="jev-step ${cls}">
          <span class="jev-phase">${PageText.html(phaseKey)}</span>
          <b>${esc(s.action || "")}</b>
          <span class="dim">${esc(s.input_value || "")}</span>
        </div>`;
      })
      .join("");

    const viewportHtml = fw.allowed
      ? `<iframe class="jev-frame" src="${esc(fw.url)}" sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" credentialless loading="lazy"></iframe>`
      : `<div class="jev-blocked">${PageText.html("jev_fw_blocked")}</div>`;

    return `<div class="jev-win" data-jev-session="${esc(d.session_id || "jev")}">
      <div class="jev-bar">
        <span class="jev-badge">JEV · ${PageText.html("jev_mode_active")}</span>
        <span class="jev-badge">${PageText.html(fw.reason)}</span>
        <input class="jev-addr" type="url" value="${esc(fw.url)}" readonly data-i18n-attr="aria-label:jev_url_label">
        <button class="jev-btn" type="button" data-jev-google>${PageText.html("jev_btn_google")}</button>
      </div>
      <div class="jev-viewport">${viewportHtml}</div>
      <div class="jev-steps">${stepsHtml}</div>
    </div>`;
  };

  Object.assign(wide, { jev_web: 1 });
})();
