(() => {
  const STEP = { done: "check", running: "play", waiting: "clock", failed: "close", pending: "" };
  const ACTIONS = { running: ["pause", "cancel"], planning: ["pause", "cancel"], paused: ["resume", "cancel"], failed: ["retry"] };
  const STATE = { failed: "bad", cancelled: "bad", paused: "warn", done: "ok" };
  const ID = /^[A-Za-z0-9_.:-]{1,80}$/;
  const post = (url) => fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" }, body: "{}" })
    .then((r) => { if (!r.ok) throw new Error(String(r.status)); });

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const id = ctx.str(d.id, 80);
      const model = ctx.str(d.model_id, 80);
      const status = ctx.str(d.status, 20).toLowerCase();
      const total = Math.max(0, Math.floor(ctx.num(d.total) || 0));
      const done = Math.min(total || Infinity, Math.max(0, Math.floor(ctx.num(d.done) || 0)));
      const progress = ctx.pct(ctx.num(d.progress) ?? (total ? (done / total) * 100 : 0));
      const steps = ctx.arr(d.steps, 40).filter((s) => s && typeof s === "object");
      const state = STATE[status] || "";
      const ui = el._ps && el._ps.id === id ? el._ps : (el._ps = { id, open: false, arm: "", busy: "", err: "" });
      clearTimeout(ui.timer);
      const actions = ID.test(id) ? ACTIONS[status] || [] : [];
      const cur = steps.findIndex((s) => s.status === "running");
      const focus = cur >= 0 ? cur : steps.findIndex((s) => s.status !== "done");
      const limit = 6;
      const from = ui.open || steps.length <= limit ? 0 : Math.max(0, Math.min(focus - 2, steps.length - limit));
      const visible = ui.open ? steps : steps.slice(from, from + limit);
      const row = (s, i) => {
        const st = STEP[s.status] !== undefined ? s.status : "pending";
        return `<li class="ps-step ${st}"><span class="ps-dot">${STEP[st] ? ctx.icon(STEP[st]) : `<b>${from + i + 1}</b>`}</span>
          <span class="ps-txt"><b>${ctx.esc(ctx.str(s.text, 140))}</b>${s.expert ? `<small>${ctx.icon("user")}${ctx.esc(ctx.str(s.expert, 60))}</small>` : ""}</span></li>`;
      };
      const btn = (a) => {
        const armed = ui.arm === a;
        const cls = a === "cancel" ? (armed ? " bad armed" : "") : a === "resume" || a === "retry" ? " primary" : "";
        return `<button type="button" class="wk-btn${cls}" data-act="${a}"${ui.busy ? " disabled" : ""}>${ctx.icon({ pause: "stop", resume: "play", cancel: "close", retry: "refresh" }[a])}<span>${ctx.esc(ui.busy === a ? ctx.t("sending") : armed ? ctx.t("confirm_cancel") : ctx.t(`action_${a}`))}</span></button>`;
      };
      const head = ctx.head({ icon: "board", label: ctx.t("label"), title: ctx.str(d.title, 80), chip: status ? ctx.t(`status_${status}`) : "", live: status === "running" || status === "planning", state });
      el.innerHTML = `${head}
        <div class="ps-hero">${ctx.ring(progress, `${Math.round(progress)}%`)}
          <div class="ps-meta"><span class="wk-sub">${ctx.esc(total ? ctx.t("steps_done", { done, total }) : ctx.t("planning"))}</span>
            ${d.current ? `<span class="ps-now">${ctx.icon("sparkle")}<span>${ctx.esc(ctx.str(d.current, 120))}</span></span>` : ""}
            ${d.expert ? `<span class="ps-exp">${ctx.icon("brain")}${ctx.esc(ctx.str(d.expert, 60))}</span>` : ""}</div></div>
        ${ctx.bar(progress, state === "ok" ? "" : state)}
        ${d.error ? `<div class="wk-alert-hint ps-err">${ctx.icon("error")}<span>${ctx.esc(ctx.str(d.error, 240))}</span></div>` : ""}
        ${ui.err ? `<div class="wk-alert-hint ps-err">${ctx.icon("alert")}<span>${ctx.esc(ui.err)}</span></div>` : ""}
        ${steps.length ? `<ol class="ps-steps">${visible.map(row).join("")}</ol>
          ${steps.length > limit ? `<button type="button" class="wk-btn ps-more" data-more="1">${ctx.esc(ui.open ? ctx.t("less") : ctx.t("all_steps", { n: steps.length }))}</button>` : ""}` : ""}
        ${actions.length || model ? `<div class="wk-actions">${actions.map(btn).join("")}${model && ID.test(model) ? `<button type="button" class="wk-btn" data-studio="1"${ui.busy ? " disabled" : ""}>${ctx.icon("cube")}<span>${ctx.esc(ctx.t("open_studio"))}</span></button>` : ""}</div>` : ""}`;
      const again = () => impl.render(el, raw, ctx);
      const run = (key, url) => {
        ui.busy = key; ui.arm = ""; ui.err = ""; again();
        post(url).then(() => { ui.busy = ""; }, () => { ui.busy = ""; ui.err = ctx.t("failed_send"); }).finally(() => { if (el.isConnected && el._ps === ui) again(); });
      };
      el.onclick = (e) => {
        const b = e.target.closest("button");
        if (!b || b.disabled) return;
        if (b.dataset.more) { ui.open = !ui.open; again(); return; }
        if (b.dataset.studio) { run("studio", `/api/models3d/${encodeURIComponent(model)}/studio/open`); return; }
        const a = b.dataset.act;
        if (!a || !actions.includes(a)) return;
        if (a === "cancel" && ui.arm !== "cancel") { ui.arm = "cancel"; again(); ui.timer = setTimeout(() => { if (ui.arm === "cancel") { ui.arm = ""; if (el.isConnected) again(); } }, 4000); return; }
        run(a, `/api/projects/${encodeURIComponent(id)}/control/${a}`);
      };
    },
    destroy(el) { if (el._ps) clearTimeout(el._ps.timer); el.onclick = null; },
  };
  NuxivaDesk.register("project_status", impl);
})();
