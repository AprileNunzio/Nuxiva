(() => {
  const ICON = { done: "✓", running: "●", waiting: "⏸", failed: "✕", pending: "○" };
  const ACTIONS = {
    running: ["pause", "cancel"],
    question: ["pause", "cancel"],
    paused: ["resume", "cancel"],
    failed: ["retry"],
  };

  const stateMap = new Map();

  function sendControl(id, action) {
    return fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/control/${encodeURIComponent(action)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }).catch(() => {});
  }

  function sendAnswer(id, qid, answer, selected) {
    return fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: qid, answer: answer || "", selected_options: selected || [] }),
    }).catch(() => {});
  }

  function sendDirective(id, text) {
    return fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/directives`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directive: text }),
    }).catch(() => {});
  }

  NuxivaDesk.register("mission_tracker", {
    render(el, d, ctx) {
      const mid = d.id || "current";
      if (!stateMap.has(mid)) {
        stateMap.set(mid, { tab: "overview", selectedOpts: new Set(), answerText: "", directiveText: "" });
      }
      const st = stateMap.get(mid);

      const navTabs = ["overview", "collab", "artifacts", "directives"]
        .map(
          (t) =>
            `<button type="button" class="mission-tab-btn ${st.tab === t ? "active" : ""}" data-tab="${t}">${ctx.esc(
              ctx.t(`tab_${t}`)
            )}</button>`
        )
        .join("");

      const chipState = d.status === "failed" ? "bad" : d.status === "done" ? "ok" : "";
      const isLive = d.status === "running" || d.status === "question";
      const headerHtml = ctx.head({
        icon: "board",
        label: ctx.t("label"),
        title: String(d.title || "").slice(0, 50),
        chip: ctx.t(`status_${d.status}`),
        live: isLive,
        state: chipState,
      });

      let contentHtml = "";

      if (st.tab === "overview") {
        const total = d.total_tasks || 0;
        const done = d.done_tasks || 0;
        const pctVal = Number(d.progress) || 0;

        let qBox = "";
        if (Array.isArray(d.questions) && d.questions.length > 0) {
          const q = d.questions[0];
          const opts = (q.options || [])
            .map(
              (opt) =>
                `<button type="button" class="mission-option-btn ${st.selectedOpts.has(opt) ? "selected" : ""}" data-opt="${ctx.esc(
                  opt
                )}">${ctx.esc(opt)}</button>`
            )
            .join("");

          qBox = `
            <div class="mission-question-box">
              <div style="font-weight:600;font-size:12px;color:#f59e0b;">${ctx.esc(ctx.t("questions_pending_title"))}</div>
              <div style="font-size:11px;">${ctx.esc(q.question)}</div>
              ${opts ? `<div class="mission-options-grid">${opts}</div>` : ""}
              <div class="mission-input-row">
                <input type="text" class="mission-input-text js-ans-input" placeholder="${ctx.esc(ctx.t("submit_answer"))}" value="${ctx.esc(
            st.answerText
          )}"/>
                <button type="button" class="mission-btn-primary js-ans-submit" data-qid="${ctx.esc(q.id)}">${ctx.esc(
            ctx.t("submit_answer")
          )}</button>
              </div>
            </div>`;
        }

        const taskRows = (d.phases || [])
          .flatMap((p) => p.tasks || [])
          .slice(0, 15)
          .map(
            (t) =>
              `<li class="wk-row ${ctx.esc(t.status)}"><span>${ICON[t.status] || "○"}</span><span><b>${ctx.esc(
                String(t.title).slice(0, 80)
              )}</b>${t.specialist_role ? `<small>${ctx.esc(t.specialist_role)}</small>` : ""}</span></li>`
          )
          .join("");

        contentHtml = `
          <div class="mission-hero-card">
            <div>
              <div class="wk-num sm">${pctVal}%</div>
              <div class="wk-sub">${ctx.esc(ctx.t("tasks_completed", { done, total }))}</div>
            </div>
            ${ctx.ring(pctVal, `${pctVal}%`)}
          </div>
          ${
            d.current_expert
              ? `<div class="mission-specialist-badge">${ctx.icon("bot")} <span><b>${ctx.esc(d.current_expert)}</b>: ${ctx.esc(
                  d.current_task || ""
                )}</span></div>`
              : ""
          }
          ${qBox}
          ${taskRows ? `<ul class="wk-list">${taskRows}</ul>` : ctx.empty(ctx.t("empty_tasks"))}
        `;
      } else if (st.tab === "collab") {
        const msgs = (d.recent_collab || [])
          .map(
            (m) => `
          <div class="mission-chat-bubble ${ctx.esc(m.kind || "")}">
            <div class="mission-chat-meta">
              <span><b>${ctx.esc(m.sender_role || m.sender_id)}</b></span>
              <span>${ctx.esc(m.kind || "")}</span>
            </div>
            <div>${ctx.esc(m.content || "")}</div>
          </div>`
          )
          .join("");

        contentHtml = `<div class="mission-chat-feed">${msgs || ctx.empty(ctx.t("no_messages"))}</div>`;
      } else if (st.tab === "artifacts") {
        contentHtml = `
          <div class="mission-hero-card">
            <span>${ctx.esc(ctx.t("tab_artifacts"))}</span>
            <b>${d.artifacts_count || 0}</b>
          </div>
          ${d.artifacts_count ? "" : ctx.empty(ctx.t("no_artifacts"))}
        `;
      } else if (st.tab === "directives") {
        contentHtml = `
          <div class="mission-input-row" style="flex-direction:column;gap:8px;">
            <textarea class="mission-input-text js-dir-input" rows="3" placeholder="${ctx.esc(
              ctx.t("add_directive_placeholder")
            )}">${ctx.esc(st.directiveText)}</textarea>
            <button type="button" class="mission-btn-primary js-dir-submit">${ctx.esc(ctx.t("send_directive"))}</button>
          </div>
        `;
      }

      const actions = (ACTIONS[d.status] || [])
        .map((a) => `<button type="button" class="wk-btn" data-act="${a}">${ctx.esc(ctx.t(`action_${a}`))}</button>`)
        .join("");

      el.innerHTML = `
        <div class="mission-widget">
          ${headerHtml}
          <div class="mission-nav">${navTabs}</div>
          <div class="mission-body">${contentHtml}</div>
          ${actions ? `<div class="wk-actions">${actions}</div>` : ""}
        </div>
      `;

      el.onclick = (e) => {
        const tabBtn = e.target.closest(".mission-tab-btn");
        if (tabBtn && tabBtn.dataset.tab) {
          st.tab = tabBtn.dataset.tab;
          NuxivaDesk.update && NuxivaDesk.update(d.id, d);
          return;
        }

        const actBtn = e.target.closest("button[data-act]");
        if (actBtn && actBtn.dataset.act) {
          sendControl(d.id, actBtn.dataset.act);
          return;
        }

        const optBtn = e.target.closest(".mission-option-btn");
        if (optBtn && optBtn.dataset.opt) {
          const opt = optBtn.dataset.opt;
          if (st.selectedOpts.has(opt)) st.selectedOpts.delete(opt);
          else st.selectedOpts.add(opt);
          optBtn.classList.toggle("selected", st.selectedOpts.has(opt));
          return;
        }

        const ansSubmit = e.target.closest(".js-ans-submit");
        if (ansSubmit) {
          const qid = ansSubmit.dataset.qid;
          const inputEl = el.querySelector(".js-ans-input");
          const ansVal = inputEl ? inputEl.value : "";
          sendAnswer(d.id, qid, ansVal, Array.from(st.selectedOpts));
          st.selectedOpts.clear();
          st.answerText = "";
          return;
        }

        const dirSubmit = e.target.closest(".js-dir-submit");
        if (dirSubmit) {
          const textEl = el.querySelector(".js-dir-input");
          if (textEl && textEl.value.trim()) {
            sendDirective(d.id, textEl.value.trim());
            st.directiveText = "";
            textEl.value = "";
          }
          return;
        }
      };

      const ansInput = el.querySelector(".js-ans-input");
      if (ansInput) {
        ansInput.oninput = (e) => {
          st.answerText = e.target.value;
        };
      }

      const dirInput = el.querySelector(".js-dir-input");
      if (dirInput) {
        dirInput.oninput = (e) => {
          st.directiveText = e.target.value;
        };
      }
    },
  });
})();
