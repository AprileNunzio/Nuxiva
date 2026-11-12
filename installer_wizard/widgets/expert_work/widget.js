(() => {
  const STATUS = new Set(["thinking", "working", "waiting", "done"]);
  const color = (c) => (/^#[0-9a-f]{6}$/i.test(c || "") ? c : "#29e0ff");
  const glyph = (s) => [...String(s || "")].slice(0, 2).join("") || "◆";
  const pretty = (tool) => tool.replace(/^skill:/, "").replace(/[_-]+/g, " ").trim();
  const span = (s) => (s >= 60 ? `${Math.floor(s / 60)}m ${String(Math.floor(s % 60)).padStart(2, "0")}s` : `${Math.floor(s)}s`);

  function stop(el) { clearInterval(el._ewT); el._ewT = 0; }

  NuxivaDesk.register("expert_work", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const status = STATUS.has(data.status) ? data.status : "thinking";
      const busy = status === "thinking" || status === "working";
      const role = ctx.str(data.role, 60);
      const given = ctx.stamp(data.started_at);
      if (!el._ewStart || el._ewRole !== role) { el._ewStart = given || ctx.now(); el._ewRole = role; el._ewSeen = given ? true : status !== "done"; }
      if (status === "done" && !el._ewEnd) el._ewEnd = ctx.now();
      if (status !== "done") el._ewEnd = 0;
      const steps = ctx.arr(data.steps, 40).slice(-8).map((s) => (s && typeof s === "object" ? { tool: ctx.str(s.tool, 60), ok: s.ok !== false } : null)).filter((s) => s && s.tool);
      const failed = steps.filter((s) => !s.ok).length;
      const question = ctx.str(data.question, 240);
      const answer = ctx.str(data.answer, 1200);
      const skill = ctx.str(data.skill || data.specialty, 80);
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: ctx.t(`status_${status}`), live: busy, state: status === "done" ? (failed ? "warn" : "ok") : "" })}
        <div class="ew-who" style="--ew:${color(data.color)}">
          <span class="ew-avatar${busy ? " busy" : ""}">${ctx.esc(glyph(data.icon))}</span>
          <div class="ew-id"><b>${ctx.esc(role || ctx.t("label"))}</b>${skill ? `<small>${ctx.esc(skill)}</small>` : ""}</div>
          <span class="ew-time wk-mono" title="${ctx.esc(ctx.t("elapsed"))}"></span>
        </div>
        ${question ? `<div class="ew-q"><span>${ctx.esc(ctx.t("question"))}</span>${ctx.esc(question)}</div>` : ""}
        ${steps.length ? `<ol class="ew-steps" aria-label="${ctx.esc(ctx.t("steps"))}">${steps.map((s, i) => `<li class="${s.ok ? "ok" : "ko"}${busy && i === steps.length - 1 ? " now" : ""}${s.tool.startsWith("skill:") ? " skill" : ""}">${s.tool.startsWith("skill:") ? ctx.icon("sparkle") : ""}${ctx.esc(pretty(s.tool))}</li>`).join("")}</ol>` : ""}
        ${busy ? `<div class="ew-dots" aria-hidden="true"><i></i><i></i><i></i></div>` : ""}
        ${status === "done" && answer ? `<div class="ew-a" tabindex="0"><span>${ctx.esc(ctx.t("answer"))}</span>${ctx.esc(answer)}</div>` : ""}`;
      const timeEl = el.querySelector(".ew-time");
      const paint = () => { if (!timeEl.isConnected) { stop(el); return; } timeEl.textContent = span(Math.max(0, (el._ewEnd || ctx.now()) - el._ewStart)); };
      if (!el._ewSeen) timeEl.hidden = true;
      else paint();
      if (el._ewSeen && (busy || status === "waiting")) el._ewT = setInterval(paint, 1000);
    },
    destroy(el) { stop(el); el._ewStart = 0; el._ewEnd = 0; },
  });
})();
