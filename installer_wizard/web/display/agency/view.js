(() => {
  const T = (key, params) => window.PageText.t("web/display", key, params);
  const STATUS = /^[a-z_]{1,24}$/;

  function make(tag, cls, key, params) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (key) window.PageText.bind(node, key, params);
    return node;
  }

  function number(n) {
    try { return new Intl.NumberFormat(document.documentElement.lang || undefined).format(n); } catch (err) { return String(n); }
  }

  function status(value) {
    return STATUS.test(value || "") ? T(`agency_status_${value}`) || value : "";
  }

  function create(root, actions) {
    const header = make("header", "ag-view-head");
    const back = make("button", "ag-btn ag-back", "agency_back"); back.type = "button";
    const titles = make("div", "ag-view-titles");
    const kicker = make("span", "ag-office-kicker", "agency_office_kicker");
    const title = make("h2", "ag-view-title");
    const sub = make("p", "ag-view-sub");
    titles.append(kicker, title, sub);
    const chip = make("span", "ag-chip");
    const brainBtn = make("button", "ag-btn ag-btn-brain", "agency_brain_title"); brainBtn.type = "button";
    const graphBtn = make("button", "ag-btn ag-btn-graph", "agency_btn_graph"); graphBtn.type = "button";
    const toggle = make("button", "ag-btn ag-toggle"); toggle.type = "button";
    header.append(back, titles, chip, brainBtn, graphBtn, toggle);

    const workspace = make("div", "ag-office-workspace");
    const stageHost = make("div", "ag-office-stage");
    const roster = make("nav", "ag-office-roster");
    const kanban = make("section", "ag-kanban");
    const drawer = make("aside", "ag-drawer"); drawer.hidden = true;
    const graphModal = make("section", "ag-graph-modal"); graphModal.hidden = true;
    const graphHead = make("div", "ag-drawer-head");
    const graphClose = make("button", "ag-btn ag-btn-sm", "agency_close"); graphClose.type = "button";
    graphHead.append(make("h3", "ag-widget-label", "agency_graph"), graphClose);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "ag-graph-svg");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    graphModal.append(graphHead, svg);

    workspace.append(stageHost, roster, kanban, drawer, graphModal);
    root.append(header, workspace);

    let current = null;
    let inspectMode = null;
    let inspectId = null;

    const office3d = window.NuxivaAgencyOffice3D.create(stageHost, {
      onSelectAgent: (agent) => openAgentDrawer(agent),
      onSelectBrain: () => openBrainDrawer(),
    });

    back.addEventListener("click", () => {
      office3d.stop();
      drawer.hidden = true;
      graphModal.hidden = true;
      actions.back();
    });

    toggle.addEventListener("click", () => {
      if (current) actions.control(current.id, current.status === "paused" ? "resume" : "pause");
    });

    brainBtn.addEventListener("click", () => openBrainDrawer());
    graphBtn.addEventListener("click", () => { graphModal.hidden = !graphModal.hidden; });
    graphClose.addEventListener("click", () => { graphModal.hidden = true; });

    function renderRoster(office) {
      roster.replaceChildren();
      const all = [office.ceo, ...(office.agents || [])].filter(Boolean);
      all.forEach((ag) => {
        const pill = make("button", `ag-roster-pill ${ag.is_ceo ? "is-ceo" : ""}`.trim());
        pill.type = "button";
        pill.dataset.status = ag.status || "idle";
        const dot = make("span", "ag-roster-dot");
        dot.style.background = ag.hoodie_color || "#ff6b1a";
        const name = make("b"); name.textContent = ag.is_ceo ? `CEO · ${ag.name}` : ag.name;
        const role = make("small"); role.textContent = ag.department || ag.role || "";
        pill.append(dot, name, role);
        pill.addEventListener("click", () => openAgentDrawer(ag));
        roster.appendChild(pill);
      });
    }

    function openAgentDrawer(agent) {
      if (!agent) return;
      inspectMode = "agent";
      inspectId = agent.id;
      office3d.select(agent.id);
      drawer.hidden = false;
      drawer.replaceChildren();

      const head = make("div", "ag-drawer-head");
      const badge = make("span", "ag-avatar-badge");
      badge.style.background = agent.hoodie_color || "#ff6b1a";
      badge.textContent = (agent.name || "A").slice(0, 2).toUpperCase();
      const hgroup = make("div", "ag-drawer-titles");
      const h3 = make("h3"); h3.textContent = agent.is_ceo ? `${agent.name} · CEO` : agent.name;
      const meta = make("p"); meta.textContent = `${agent.department || "NunzioTech Agency"} · ${agent.role || ""}`;
      hgroup.append(h3, meta);
      const closeBtn = make("button", "ag-btn ag-btn-sm", "agency_close"); closeBtn.type = "button";
      closeBtn.addEventListener("click", () => { drawer.hidden = true; inspectMode = null; office3d.select(null); });
      head.append(badge, hgroup, closeBtn);

      const thoughtBox = make("section", "ag-drawer-sec ag-thought-box");
      thoughtBox.append(make("h4", "ag-sec-label", "agency_what_doing"));
      const thoughtText = make("p", "ag-thought-text");
      thoughtText.textContent = agent.thought || status(agent.status);
      thoughtBox.appendChild(thoughtText);

      const skillsBox = make("section", "ag-drawer-sec");
      skillsBox.append(make("h4", "ag-sec-label", "agency_skills"));
      const tagWrap = make("div", "ag-skill-tags");
      (agent.skills || []).forEach((sk) => {
        const tag = make("span", "ag-skill-tag");
        tag.textContent = sk;
        tagWrap.appendChild(tag);
      });
      skillsBox.appendChild(tagWrap);

      const promptDetails = make("details", "ag-drawer-sec ag-prompt-details");
      const summary = make("summary", "ag-sec-label", "agency_system_prompt");
      const promptPre = make("pre", "ag-prompt-pre");
      promptPre.textContent = agent.system_prompt || "";
      promptDetails.append(summary, promptPre);

      const tasksSec = make("section", "ag-drawer-sec");
      tasksSec.append(make("h4", "ag-sec-label", "agency_w_tasks"));
      const agentTasks = (agent.tasks && agent.tasks.length)
        ? agent.tasks
        : (current && current.tasks ? current.tasks : []);

      if (!agentTasks.length) {
        tasksSec.appendChild(make("p", "ag-muted", "agency_none"));
      } else {
        const list = make("div", "ag-drawer-tasks");
        agentTasks.forEach((t) => {
          const card = make("div", "ag-task-item");
          card.dataset.status = t.status || "pending";
          const top = make("div", "ag-task-top");
          const tt = make("b"); tt.textContent = t.title;
          const stChip = make("span", "ag-chip ag-chip-xs"); stChip.textContent = status(t.status);
          top.append(tt, stChip);

          const noteInput = make("input", "ag-task-input");
          noteInput.type = "text";
          noteInput.placeholder = T("agency_edit_placeholder") || "Direttiva / modifica...";

          const btnRow = make("div", "ag-task-actions");
          const approveBtn = make("button", "ag-action-btn", "agency_btn_approve"); approveBtn.type = "button";
          approveBtn.addEventListener("click", () => actions.taskAction(current.id, t.id, "approve", {}));

          const modifyBtn = make("button", "ag-action-btn ag-action-alt", "agency_btn_reject"); modifyBtn.type = "button";
          modifyBtn.addEventListener("click", () => {
            actions.taskAction(current.id, t.id, "modify", { notes: noteInput.value.trim() || "Revisione richiesta dal supervisore" });
            noteInput.value = "";
          });

          const stopBtn = make("button", "ag-action-btn ag-action-danger", "agency_btn_interrupt"); stopBtn.type = "button";
          stopBtn.addEventListener("click", () => actions.taskAction(current.id, t.id, "interrupt", { reason: noteInput.value.trim() }));

          btnRow.append(approveBtn, modifyBtn, stopBtn);
          card.append(top, noteInput, btnRow);
          list.appendChild(card);
        });
        tasksSec.appendChild(list);
      }

      drawer.append(head, thoughtBox, skillsBox, promptDetails, tasksSec);
    }

    function openBrainDrawer() {
      if (!current || !current.office) return;
      const brain = current.office.shared_brain || {};
      inspectMode = "brain";
      inspectId = "shared_brain";
      office3d.select("shared_brain");
      drawer.hidden = false;
      drawer.replaceChildren();

      const head = make("div", "ag-drawer-head");
      const badge = make("span", "ag-avatar-badge is-brain"); badge.textContent = "AI";
      const hgroup = make("div", "ag-drawer-titles");
      const h3 = make("h3", "", "agency_brain_title");
      const meta = make("p", "", "agency_brain_propagate");
      hgroup.append(h3, meta);
      const closeBtn = make("button", "ag-btn ag-btn-sm", "agency_close"); closeBtn.type = "button";
      closeBtn.addEventListener("click", () => { drawer.hidden = true; inspectMode = null; office3d.select(null); });
      head.append(badge, hgroup, closeBtn);

      const metrics = make("section", "ag-drawer-sec ag-brain-metrics");
      const m1 = make("div", "ag-brain-stat");
      const b1 = make("b"); b1.textContent = number(brain.rules_count || 1687);
      m1.append(b1, make("span", "", "agency_brain_rules", { n: number(brain.rules_count || 1687) }));
      const m2 = make("div", "ag-brain-stat");
      const b2 = make("b"); b2.textContent = number(brain.reviews_count || 943);
      m2.append(b2, make("span", "", "agency_brain_reviews", { n: number(brain.reviews_count || 943) }));
      metrics.append(m1, m2);

      const decSec = make("section", "ag-drawer-sec");
      decSec.append(make("h4", "ag-sec-label", "agency_brain_decisions"));
      const decs = brain.decisions || [];
      if (!decs.length) {
        decSec.appendChild(make("p", "ag-muted", "agency_none"));
      } else {
        const ul = make("ul", "ag-list");
        decs.forEach((d) => {
          const li = make("li");
          const b = make("b"); b.textContent = d.topic;
          const s = make("span"); s.textContent = d.ruling;
          li.append(b, s);
          ul.appendChild(li);
        });
        decSec.appendChild(ul);
      }

      const criticSec = make("section", "ag-drawer-sec");
      criticSec.append(make("h4", "ag-sec-label", "agency_w_critic"));
      const qs = brain.critic_exchanges || current.questions || [];
      if (!qs.length) {
        criticSec.appendChild(make("p", "ag-muted", "agency_none"));
      } else {
        const ul = make("ul", "ag-list");
        qs.forEach((q) => {
          const li = make("li");
          const b = make("b"); b.textContent = q.q;
          const s = make("span"); s.textContent = q.a;
          li.append(b, s);
          ul.appendChild(li);
        });
        criticSec.appendChild(ul);
      }

      drawer.append(head, metrics, decSec, criticSec);
    }

    function renderKanban(office) {
      kanban.replaceChildren();
      const kb = (office && office.kanban) || { to_watch: [], to_approve: [], in_progress: [] };
      const cols = [
        { key: "agency_col_watch", items: kb.to_watch || [], kind: "watch" },
        { key: "agency_col_approve", items: kb.to_approve || [], kind: "approve" },
        { key: "agency_col_progress", items: kb.in_progress || [], kind: "progress" },
      ];

      cols.forEach((col) => {
        const colBox = make("div", "ag-kanban-col");
        const colHead = make("div", "ag-kanban-head");
        const h4 = make("h4", "", col.key);
        const count = make("span", "ag-kanban-count"); count.textContent = String(col.items.length);
        colHead.append(h4, count);
        const body = make("div", "ag-kanban-body");

        if (!col.items.length) {
          body.appendChild(make("p", "ag-muted", "agency_none"));
        } else {
          col.items.slice(0, 4).forEach((item) => {
            const card = make("article", "ag-kcard");
            const titleEl = make("b", "ag-kcard-title"); titleEl.textContent = item.title;
            const subEl = make("span", "ag-kcard-sub"); subEl.textContent = item.subtitle || item.agent_id || "";
            const actRow = make("div", "ag-kcard-actions");

            if (item.kind === "question") {
              const input = make("input", "ag-kcard-input");
              input.type = "text";
              input.placeholder = T("agency_edit_placeholder") || "Rispondi...";
              const replyBtn = make("button", "ag-action-btn", "agency_btn_reply"); replyBtn.type = "button";
              replyBtn.addEventListener("click", () => {
                if (input.value.trim()) actions.answerQuestion(current.id, item.id, input.value.trim());
              });
              actRow.append(input, replyBtn);
            } else {
              const appBtn = make("button", "ag-action-btn", "agency_btn_approve"); appBtn.type = "button";
              appBtn.addEventListener("click", () => actions.taskAction(current.id, item.id, "approve", {}));
              const rejBtn = make("button", "ag-action-btn ag-action-alt", "agency_btn_reject"); rejBtn.type = "button";
              rejBtn.addEventListener("click", () => actions.taskAction(current.id, item.id, "rework", { notes: "Richiesta revisione" }));
              actRow.append(appBtn, rejBtn);
            }

            card.append(titleEl, subEl, actRow);
            body.appendChild(card);
          });
        }
        colBox.append(colHead, body);
        kanban.appendChild(colBox);
      });
    }

    function render(p) {
      current = p;
      const office = p.office || {};
      title.textContent = `${office.agency_name || "NunzioTech Agency"} — ${p.title}`;
      sub.textContent = p.summary || p.goal || "";
      chip.textContent = `${status(p.status)} · ${p.percent || 0}%`;
      chip.dataset.status = p.status;
      toggle.hidden = !["running", "paused"].includes(p.status);
      window.PageText.bind(toggle, p.status === "paused" ? "agency_resume" : "agency_pause");

      office3d.update(office);
      renderRoster(office);
      renderKanban(office);
      window.NuxivaAgencyGraph.render(svg, p.tasks || [], status);

      if (!drawer.hidden && inspectMode === "brain") {
        openBrainDrawer();
      } else if (!drawer.hidden && inspectMode === "agent" && inspectId) {
        const all = [office.ceo, ...(office.agents || [])].filter(Boolean);
        const found = all.find((a) => a.id === inspectId);
        if (found) openAgentDrawer(found);
      }
    }

    return { render, get current() { return current; } };
  }

  window.NuxivaAgencyView = { create, status };
})();
