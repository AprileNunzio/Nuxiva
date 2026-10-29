(() => {
  const STATUSES = new Set(["planning", "question", "running", "paused", "done", "failed", "cancelled"]);
  const TASK_ICON = { done: "check", running: "refresh", review: "eye", waiting: "clock", failed: "close", pending: "" };
  const ACTIONS = { planning: ["pause", "cancel"], running: ["pause", "cancel"], question: ["pause", "cancel"], paused: ["resume", "cancel"], failed: ["retry"] };
  const TABS = ["overview", "collab", "artifacts", "directives"];
  const ID = /^[A-Za-z0-9_-]{1,80}$/;
  const states = new Map();

  const api = async (id, path, body) => {
    try {
      const r = await fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}), credentials: "same-origin" });
      return r.ok;
    } catch { return false; }
  };

  function stateOf(id) {
    if (!states.has(id)) {
      if (states.size > 20) states.delete(states.keys().next().value);
      states.set(id, { tab: "overview", picked: new Set(), answer: "", directive: "", armed: "", busy: "", flash: "" });
    }
    return states.get(id);
  }

  const initials = (s) => s.split(/[\s_-]+/).filter(Boolean).slice(0, 2).map((w) => Array.from(w)[0]).join("").toUpperCase() || "?";

  function overview(m, st, ctx) {
    const pct = Math.max(0, Math.min(100, Math.round(ctx.num(m.progress) || 0)));
    const total = Math.max(0, Math.floor(ctx.num(m.total_tasks) || 0)), done = Math.max(0, Math.floor(ctx.num(m.done_tasks) || 0));
    const expert = ctx.str(m.current_expert, 60), task = ctx.str(m.current_task, 160), error = ctx.str(m.error, 300);
    const q = ctx.arr(m.questions, 5).find((x) => x && typeof x === "object" && ctx.str(x.question, 600) && ID.test(String(x.id || "")));
    const phases = ctx.arr(m.phases, 12).filter((p) => p && typeof p === "object");
    const opts = q ? ctx.arr(q.options, 8).map((o) => ctx.str(o, 120)).filter(Boolean) : [];
    return `<div class="mt-hero">${ctx.ring(pct, `${pct}%`)}<div class="mt-hero-txt"><span class="wk-sub">${ctx.esc(ctx.t("tasks_completed", { done, total }))}</span>
        ${ctx.str(m.goal, 300) ? `<span class="mt-goal">${ctx.esc(ctx.str(m.goal, 300))}</span>` : ""}</div></div>
      ${error ? `<div class="wk-alert bad mt-error">${ctx.icon("error")}<span>${ctx.esc(error)}</span></div>` : ""}
      ${expert || task ? `<div class="mt-expert"><span class="mt-avatar" aria-hidden="true">${ctx.esc(initials(expert || "AI"))}</span><span><b>${ctx.esc(expert || ctx.t("active_specialist"))}</b><small>${ctx.esc(task)}</small></span><i class="mt-dots" aria-hidden="true"><i></i><i></i><i></i></i></div>` : ""}
      ${q ? `<div class="mt-question"><h5>${ctx.icon("chat")}${ctx.esc(ctx.t("questions_pending_title"))}</h5><p>${ctx.esc(ctx.str(q.question, 600))}</p>
        ${opts.length ? `<div class="mt-opts" role="${q.is_multi_select ? "group" : "radiogroup"}">${opts.map((o) => `<button type="button" class="mt-opt${st.picked.has(o) ? " on" : ""}" data-opt="${ctx.esc(o)}" aria-pressed="${st.picked.has(o)}">${ctx.esc(o)}</button>`).join("")}</div>` : ""}
        <form class="mt-row js-answer" data-qid="${ctx.esc(String(q.id))}" data-multi="${q.is_multi_select ? 1 : 0}"><input class="mt-input" maxlength="500" value="${ctx.esc(st.answer)}" placeholder="${ctx.esc(ctx.t("answer_placeholder"))}" autocomplete="off">
          <button type="submit" class="mt-primary"${st.busy === "answer" ? " disabled" : ""}>${ctx.esc(ctx.t("submit_answer"))}</button></form></div>` : ""}
      ${phases.length ? `<div class="mt-phases">${phases.map((p) => {
        const tasks = ctx.arr(p.tasks, 30).filter((t) => t && typeof t === "object");
        const pd = tasks.filter((t) => t.status === "done").length;
        const active = tasks.some((t) => t.status === "running" || t.status === "review");
        return `<details class="mt-phase"${active || (pd < tasks.length && !phases.some((x) => x !== p && ctx.arr(x.tasks, 30).some((t) => t && (t.status === "running" || t.status === "review")))) ? " open" : ""}>
          <summary><span>${ctx.esc(ctx.str(p.title, 80) || ctx.t("phase"))}</span><span class="mono">${pd}/${tasks.length}</span>${ctx.bar(tasks.length ? (pd / tasks.length) * 100 : 0, pd === tasks.length && tasks.length ? "ok" : "")}</summary>
          <ul class="mt-tasks">${tasks.slice(0, 15).map((t) => {
            const s = Object.hasOwn(TASK_ICON, t.status) ? t.status : "pending";
            return `<li class="${s}"><span class="mt-ic" title="${ctx.esc(ctx.t(`task_${s}`))}">${TASK_ICON[s] ? ctx.icon(TASK_ICON[s]) : "<i></i>"}</span><span><b>${ctx.esc(ctx.str(t.title, 100))}</b>${ctx.str(t.specialist_role, 40) ? `<small>${ctx.esc(ctx.str(t.specialist_role, 40))}</small>` : ""}</span></li>`;
          }).join("")}</ul></details>`;
      }).join("")}</div>` : ctx.empty(ctx.t("empty_tasks"))}`;
  }

  function collab(m, ctx) {
    const msgs = ctx.arr(m.recent_collab, 8).filter((x) => x && typeof x === "object" && ctx.str(x.content, 10));
    if (!msgs.length) return ctx.empty(ctx.t("no_messages"));
    return `<div class="mt-feed">${msgs.map((x) => {
      const who = ctx.pick(x, ["sender_role", "sender_id"], 40) || "?";
      const kind = ctx.str(x.kind, 20).toLowerCase().replace(/[^a-z_]/g, "");
      const at = ctx.stamp(x.timestamp);
      return `<div class="mt-msg ${kind}"><span class="mt-avatar sm" aria-hidden="true">${ctx.esc(initials(who))}</span><div><div class="mt-meta"><b>${ctx.esc(who)}</b>${kind ? `<span class="mt-kind">${ctx.esc(kind)}</span>` : ""}${at ? `<span>${ctx.esc(ctx.ago(at))}</span>` : ""}</div><p>${ctx.esc(ctx.str(x.content, 1200))}</p></div></div>`;
    }).join("")}</div>`;
  }

  function artifacts(m, ctx) {
    const n = Math.max(0, Math.floor(ctx.num(m.artifacts_count) || 0));
    return n ? `<div class="mt-art">${ctx.icon("file")}<b class="wk-num sm">${n}</b><span class="wk-sub">${ctx.esc(ctx.count("artifacts", n))}</span></div>` : ctx.empty(ctx.t("no_artifacts"));
  }

  function directives(st, ctx) {
    return `<form class="mt-dir js-directive"><textarea class="mt-input" rows="3" maxlength="500" placeholder="${ctx.esc(ctx.t("add_directive_placeholder"))}">${ctx.esc(st.directive)}</textarea>
      <div class="mt-row"><span class="wk-faint mt-count">${st.directive.length}/500</span><button type="submit" class="mt-primary"${st.busy === "directive" ? " disabled" : ""}>${ctx.esc(ctx.t("send_directive"))}</button></div></form>`;
  }

  const impl = {
    render(el, d, ctx) {
      const m = d && typeof d === "object" ? d : {};
      const id = ID.test(String(m.id || "")) ? String(m.id) : "";
      const st = stateOf(id || "_");
      const status = STATUSES.has(m.status) ? m.status : "planning";
      el._mt = { d: m, ctx };
      const head = ctx.head({ icon: "board", label: ctx.t("label"), title: ctx.str(m.title, 60), chip: ctx.t(`status_${status}`), live: status === "running" || status === "question" || status === "planning", state: status === "failed" ? "bad" : status === "done" ? "ok" : status === "question" || status === "paused" ? "warn" : "" });
      if (!id) { el.innerHTML = `${ctx.head({ icon: "board", label: ctx.t("label") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const questions = ctx.arr(m.questions, 5).length;
      const body = st.tab === "collab" ? collab(m, ctx) : st.tab === "artifacts" ? artifacts(m, ctx) : st.tab === "directives" ? directives(st, ctx) : overview(m, st, ctx);
      const actions = ACTIONS[status] || [];
      el.innerHTML = `<div class="mt">${head}
        <div class="mt-tabs" role="tablist">${TABS.map((t) => `<button type="button" role="tab" class="mt-tab${st.tab === t ? " on" : ""}" data-tab="${t}" aria-selected="${st.tab === t}">${ctx.esc(ctx.t(`tab_${t}`))}${t === "overview" && questions ? `<i class="mt-badge">${questions}</i>` : ""}</button>`).join("")}</div>
        <div class="mt-body">${body}</div>
        ${st.flash ? `<div class="mt-flash ${st.flash === "ok" ? "ok" : "bad"}" role="status">${ctx.esc(ctx.t(st.flash === "ok" ? "sent" : "send_failed"))}</div>` : ""}
        ${actions.length ? `<div class="wk-actions mt-actions">${actions.map((a) => `<button type="button" class="wk-btn${a === "cancel" ? " danger" : a === "resume" || a === "retry" ? " primary" : ""}${st.armed === a ? " armed" : ""}" data-act="${a}"${st.busy === a ? " disabled" : ""}>${ctx.esc(st.armed === a ? ctx.t("confirm_cancel") : ctx.t(`action_${a}`))}</button>`).join("")}</div>` : ""}</div>`;
      st.flash = "";
      const again = () => { if (el.isConnected && el._mt) impl.render(el, el._mt.d, el._mt.ctx); };
      el.onclick = async (e) => {
        const tab = e.target.closest("[data-tab]");
        if (tab) { e.stopPropagation(); st.tab = tab.dataset.tab; again(); return; }
        const opt = e.target.closest("[data-opt]");
        if (opt) {
          e.stopPropagation();
          const form = el.querySelector(".js-answer"), v = opt.dataset.opt;
          if (form && form.dataset.multi !== "1") { const was = st.picked.has(v); st.picked.clear(); if (!was) st.picked.add(v); }
          else if (st.picked.has(v)) st.picked.delete(v); else st.picked.add(v);
          el.querySelectorAll("[data-opt]").forEach((b) => { b.classList.toggle("on", st.picked.has(b.dataset.opt)); b.setAttribute("aria-pressed", String(st.picked.has(b.dataset.opt))); });
          return;
        }
        const act = e.target.closest("[data-act]");
        if (act) {
          e.stopPropagation();
          const a = act.dataset.act;
          if (a === "cancel" && st.armed !== "cancel") { st.armed = "cancel"; again(); setTimeout(() => { if (st.armed === "cancel") { st.armed = ""; again(); } }, 4000); return; }
          st.armed = ""; st.busy = a; again();
          const ok = await api(id, `control/${a}`);
          st.busy = ""; st.flash = ok ? "" : "bad"; again();
        }
      };
      const answer = el.querySelector(".js-answer");
      if (answer) {
        const input = answer.querySelector("input");
        input.addEventListener("input", () => { st.answer = input.value; });
        answer.addEventListener("submit", async (e) => {
          e.preventDefault();
          if (!input.value.trim() && !st.picked.size) return;
          st.busy = "answer"; again();
          const ok = await api(id, "answer", { question_id: answer.dataset.qid, answer: st.answer.slice(0, 500), selected_options: [...st.picked].slice(0, 8) });
          st.busy = ""; st.flash = ok ? "ok" : "bad";
          if (ok) { st.answer = ""; st.picked.clear(); }
          again();
        });
      }
      const dir = el.querySelector(".js-directive");
      if (dir) {
        const area = dir.querySelector("textarea"), count = dir.querySelector(".mt-count");
        area.addEventListener("input", () => { st.directive = area.value; count.textContent = `${area.value.length}/500`; });
        dir.addEventListener("submit", async (e) => {
          e.preventDefault();
          const text = area.value.trim();
          if (!text) return;
          st.busy = "directive"; again();
          const ok = await api(id, "directives", { directive: text.slice(0, 500) });
          st.busy = ""; st.flash = ok ? "ok" : "bad";
          if (ok) st.directive = "";
          again();
        });
      }
    },
    destroy(el) { el.onclick = null; el._mt = null; },
  };
  NuxivaDesk.register("mission_tracker", impl);
})();
