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

  function widget(label, cls = "") {
    const box = make("article", `ag-widget ${cls}`.trim());
    const head = make("h3", "ag-widget-label", label);
    const body = make("div", "ag-widget-body");
    box.append(head, body);
    return { box, body };
  }

  function ring(percent) {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 120 120");
    svg.setAttribute("class", "ag-ring");
    const track = document.createElementNS(NS, "circle");
    const bar = document.createElementNS(NS, "circle");
    [track, bar].forEach((c) => { c.setAttribute("cx", "60"); c.setAttribute("cy", "60"); c.setAttribute("r", "50"); });
    track.setAttribute("class", "ag-ring-track");
    bar.setAttribute("class", "ag-ring-bar");
    const length = 2 * Math.PI * 50;
    bar.setAttribute("stroke-dasharray", `${(percent / 100) * length} ${length}`);
    const text = document.createElementNS(NS, "text");
    text.setAttribute("x", "60"); text.setAttribute("y", "68"); text.setAttribute("text-anchor", "middle");
    text.textContent = `${percent}%`;
    svg.append(track, bar, text);
    return svg;
  }

  function list(items, render) {
    const ul = make("ul", "ag-list");
    items.forEach((item) => { const li = document.createElement("li"); render(li, item); ul.appendChild(li); });
    return ul;
  }

  function stat(key, value, params) {
    const row = make("div", "ag-stat");
    const v = make("b"); v.textContent = value;
    row.append(v, make("span", "", key, params));
    return row;
  }

  function create(root, actions) {
    const header = make("header", "ag-view-head");
    const back = make("button", "ag-btn ag-back", "agency_back"); back.type = "button";
    const titles = make("div", "ag-view-titles");
    const title = make("h2", "ag-view-title");
    const sub = make("p", "ag-view-sub");
    titles.append(title, sub);
    const chip = make("span", "ag-chip");
    const toggle = make("button", "ag-btn ag-toggle"); toggle.type = "button";
    header.append(back, titles, chip, toggle);
    const grid = make("div", "ag-widgets");
    const graphBox = make("section", "ag-graph");
    graphBox.append(make("h3", "ag-widget-label", "agency_graph"));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "ag-graph-svg");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    graphBox.appendChild(svg);
    root.append(header, grid, graphBox);
    let current = null;

    back.addEventListener("click", () => actions.back());
    toggle.addEventListener("click", () => {
      if (current) actions.control(current.id, current.status === "paused" ? "resume" : "pause");
    });

    function render(p) {
      current = p;
      title.textContent = p.title;
      sub.textContent = p.summary || p.goal || "";
      chip.textContent = status(p.status);
      chip.dataset.status = p.status;
      toggle.hidden = !["running", "paused"].includes(p.status);
      window.PageText.bind(toggle, p.status === "paused" ? "agency_resume" : "agency_pause");
      grid.replaceChildren();

      const progress = widget("agency_w_progress", "ag-w-progress");
      progress.body.append(ring(p.percent), make("p", "ag-muted", "agency_tasks_count", { done: p.counts.done, total: p.counts.total }));
      const tasks = widget("agency_w_tasks");
      tasks.body.append(stat("agency_task_running", number(p.counts.running)), stat("agency_task_review", number(p.counts.review)),
        stat("agency_task_pending", number(p.counts.pending)), stat("agency_task_failed", number(p.counts.failed)));
      const usage = widget("agency_w_tokens");
      usage.body.append(stat("agency_tokens_of", number(p.tokens), { budget: number(p.budget_tokens) }),
        stat("agency_eta", number(Math.ceil(p.eta_seconds / 60))), stat("agency_worked", number(Math.ceil(p.seconds / 60))));
      const team = widget("agency_w_team");
      team.body.appendChild(list(p.roles, (li, r) => {
        const b = make("b"); b.textContent = r.id;
        const s = make("span"); s.textContent = r.mission;
        li.append(b, s);
      }));
      const critic = widget("agency_w_critic", "ag-w-wide");
      critic.body.appendChild(p.questions.length ? list(p.questions, (li, q) => {
        const b = make("b"); b.textContent = q.q;
        const s = make("span"); s.textContent = q.a;
        li.append(b, s);
      }) : make("p", "ag-muted", "agency_none"));
      const forged = widget("agency_w_tools");
      forged.body.appendChild(p.tools.length ? list(p.tools, (li, t) => { li.textContent = t; }) : make("p", "ag-muted", "agency_none"));
      grid.append(progress.box, tasks.box, usage.box, team.box, forged.box, critic.box);
      window.NuxivaAgencyGraph.render(svg, p.tasks, status);
    }

    return { render, get current() { return current; } };
  }

  window.NuxivaAgencyView = { create, status };
})();
