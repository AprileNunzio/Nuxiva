(() => {
  const D = window.NuxivaDisplay;
  if (!D || !D.stagePanels) return;
  const { fmt } = D;
  const { render, wide } = D.stagePanels;
  const esc = fmt.esc;

  function sanitizeUrl(raw) {
    const clean = String(raw || "").trim();
    if (!/^https?:\/\//i.test(clean)) {
      return `https://www.google.com/search?q=${encodeURIComponent(clean)}`;
    }
    return clean;
  }

  render.jev_web = (p) => {
    const d = p.data || {};
    const url = sanitizeUrl(d.entry_url || d.url || "https://www.google.com");
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

    return `<div class="jev-win" data-jev-session="${esc(d.session_id || "jev")}">
      <div class="jev-bar">
        <span class="jev-badge">JEV · ${PageText.html("jev_mode_active")}</span>
        <input class="jev-addr" type="url" value="${esc(url)}" readonly data-i18n-attr="aria-label:jev_url_label">
        <button class="jev-btn" type="button" data-jev-google>${PageText.html("jev_btn_google")}</button>
      </div>
      <div class="jev-viewport">
        <iframe class="jev-frame" src="${esc(url)}" sandbox="allow-scripts allow-forms allow-same-origin" referrerpolicy="no-referrer" loading="lazy"></iframe>
      </div>
      <div class="jev-steps">${stepsHtml}</div>
    </div>`;
  };

  Object.assign(wide, { jev_web: 1 });
})();
