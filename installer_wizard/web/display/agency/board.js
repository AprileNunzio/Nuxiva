(() => {
  const D = window.NuxivaDisplay;
  const T = (key, params) => window.PageText.t("web/display", key, params);
  const POLL_MS = 3000, IDLE_POLL_MS = 15000;
  const st = { open: false, focus: null, timer: 0, data: null, offline: false, seq: 0 };
  const root = document.getElementById("agency-board");
  if (!D || !root) return;

  const make = (tag, cls, key, params) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (key) window.PageText.bind(node, key, params);
    return node;
  };

  const sky = make("canvas", "ag-sky");
  const galaxyBox = make("div", "ag-galaxy");
  const head = make("header", "ag-head");
  const titles = make("div", "ag-titles");
  titles.append(make("h2", "ag-title", "agency_title"), make("p", "ag-sub", "agency_sub"));
  const agents = make("span", "ag-chip ag-agents");
  const tools = make("span", "ag-chip ag-tools");
  const close = make("button", "ag-btn ag-close", "agency_close"); close.type = "button";
  head.append(titles, agents, tools, close);
  const planets = make("div", "ag-planets");
  const notice = make("p", "ag-notice");
  const hint = make("p", "ag-hint", "agency_hint");
  galaxyBox.append(head, planets, notice, hint);
  const viewRoot = make("section", "ag-view"); viewRoot.hidden = true;
  root.append(sky, galaxyBox, viewRoot);

  const galaxy = window.NuxivaAgencyGalaxy.create(sky, planets, (id) => openProject(id));
  const view = window.NuxivaAgencyView.create(viewRoot, { back: () => backToGalaxy(), control: (id, action) => control(id, action) });

  async function request(path, options = {}) {
    const res = await fetch(path, { credentials: "same-origin", cache: "no-store", ...options,
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1", ...(options.headers || {}) } });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }

  function renderOverview(data) {
    st.data = data;
    window.PageText.bind(agents, "agency_agents", { running: data.agents.running, parallel: data.agents.parallel });
    window.PageText.bind(tools, "agency_tools", { n: data.tools });
    galaxy.update(data.projects);
    notice.hidden = data.projects.length > 0 && !st.offline;
    if (st.offline) window.PageText.bind(notice, "agency_offline");
    else if (!data.projects.length) window.PageText.bind(notice, "agency_empty");
  }

  async function refresh() {
    try {
      if (st.focus) view.render(await request(`/api/agency/board/${encodeURIComponent(st.focus)}`));
      else { st.offline = false; renderOverview(await request("/api/agency/board")); }
    } catch (err) {
      if (!st.focus) { st.offline = true; renderOverview(st.data || { agents: { running: 0, parallel: 0 }, tools: 0, projects: [] }); }
    }
  }

  function schedule() {
    clearTimeout(st.timer);
    if (!st.open) return;
    st.timer = setTimeout(async () => { await refresh(); schedule(); }, document.hidden ? IDLE_POLL_MS : POLL_MS);
  }

  function open() {
    if (st.open) return;
    st.open = true;
    root.hidden = false;
    document.body.classList.add("agency-open");
    galaxy.start();
    refresh().then(schedule);
    close.focus({ preventScroll: true });
  }

  function shut() {
    st.open = false; st.focus = null;
    clearTimeout(st.timer);
    galaxy.stop();
    galaxy.calm(false);
    root.hidden = true; viewRoot.hidden = true; galaxyBox.hidden = false;
    document.body.classList.remove("agency-open");
  }

  async function openProject(id) {
    if (!id) return;
    open();
    st.focus = id;
    galaxy.calm(true);
    galaxyBox.hidden = true; viewRoot.hidden = false;
    await refresh();
    schedule();
  }

  function backToGalaxy() {
    st.focus = null;
    galaxy.calm(false);
    viewRoot.hidden = true; galaxyBox.hidden = false;
    refresh().then(schedule);
  }

  async function control(id, action) {
    try { view.render(await request(`/api/agency/board/${encodeURIComponent(id)}/${action}`, { method: "POST", body: "{}" })); return true; }
    catch (err) { return false; }
  }

  function plain(text) {
    return String(text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function find(name) {
    const words = plain(name).split(/[^a-z0-9]+/).filter((w) => w.length > 2);
    const projects = (st.data && st.data.projects) || [];
    let best = null, score = 0;
    projects.forEach((p) => {
      const hay = plain(p.title);
      const s = words.filter((w) => hay.includes(w)).length;
      if (s > score) { best = p; score = s; }
    });
    return best;
  }

  function pattern(key) {
    const source = T(key);
    if (!source) return null;
    try { return new RegExp(source, "iu"); } catch (err) { return null; }
  }

  function say(key, params, lang) {
    const text = T(key, params);
    if (!text) return;
    D.$("you").textContent = "";
    D.typeInto(D.$("say"), text);
    if (D.speak) D.speak(text, lang);
  }

  async function voice(text, lang) {
    const create = pattern("agency_cmd_create");
    const made = create && create.exec(text);
    if (made && made.groups && made.groups.goal && made.groups.goal.trim().length >= 8) {
      try {
        await request("/api/agency/board/projects", { method: "POST", body: JSON.stringify({ goal: text.trim().slice(0, 2000) }) });
        open(); say("agency_started", {}, lang);
      } catch (err) { say("agency_offline", {}, lang); }
      return true;
    }
    const opened = pattern("agency_cmd_open");
    const hit = opened && opened.exec(text);
    if (hit && hit.groups && hit.groups.name) {
      if (!st.data) await request("/api/agency/board").then((d) => { st.data = d; }).catch(() => {});
      const project = find(hit.groups.name);
      if (project) { await openProject(project.id); say("agency_opened", { title: project.title }, lang); }
      else say("agency_not_found_say", {}, lang);
      return true;
    }
    const showing = pattern("agency_cmd_show");
    if (showing && showing.test(text)) { open(); if (st.focus) backToGalaxy(); say("agency_shown", {}, lang); return true; }
    if (!st.open) return false;
    const closing = pattern("agency_cmd_close");
    if (closing && closing.test(text)) { shut(); return true; }
    const current = view.current;
    for (const action of ["pause", "resume"]) {
      const re = pattern(`agency_cmd_${action}`);
      if (st.focus && current && re && re.test(text)) {
        if (await control(current.id, action)) say(`agency_${action}d_say`, {}, lang);
        return true;
      }
    }
    for (const [key, delta] of [["agency_cmd_next", 1], ["agency_cmd_prev", -1]]) {
      const re = pattern(key);
      if (re && re.test(text)) { const id = galaxy.step(delta); if (st.focus && id) openProject(id); return true; }
    }
    return false;
  }

  const ask = D.ask;
  D.ask = async (text, lang, heard = {}) => {
    D.lastInteraction = Date.now();
    if (typeof text === "string" && text.length <= 600 && await voice(text, lang)) return;
    return ask(text, lang, heard);
  };

  const setMode = D.setMode;
  D.setMode = (mode) => { if (st.open && mode !== "face") shut(); return setMode(mode); };

  window.addEventListener("nuxiva-hand-gesture", (event) => {
    if (!st.open || !event.detail) return;
    const name = event.detail.gesture;
    if (name === "swipe.left" || name === "swipe.right") {
      const id = galaxy.step(name === "swipe.left" ? 1 : -1);
      if (st.focus && id) openProject(id);
    } else if (name === "swipe.up" && !st.focus) openProject(galaxy.selected);
    else if (name === "swipe.down") { if (st.focus) backToGalaxy(); else shut(); }
  });

  window.addEventListener("keydown", (event) => {
    if (!st.open) return;
    if (event.key === "Escape") { if (st.focus) backToGalaxy(); else shut(); }
    else if (!st.focus && (event.key === "ArrowRight" || event.key === "ArrowLeft")) galaxy.step(event.key === "ArrowRight" ? 1 : -1);
    else if (!st.focus && event.key === "Enter" && document.activeElement === close) openProject(galaxy.selected);
  });

  close.addEventListener("click", shut);
  const button = document.getElementById("btn-agency");
  if (button) button.addEventListener("click", () => { D.lastInteraction = Date.now(); if (st.open) shut(); else open(); });
  document.addEventListener("visibilitychange", () => { if (st.open && !document.hidden) refresh(); });

  const ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;

  function sync(intent) {
    if (!intent || typeof intent !== "object" || !Number.isInteger(intent.seq) || intent.seq <= st.seq) return;
    st.seq = intent.seq;
    D.lastInteraction = Date.now();
    if (intent.view === "close") shut();
    else if (intent.view === "project" && ID.test(intent.id || "")) openProject(intent.id);
    else if (intent.view === "galaxy") { open(); if (st.focus) backToGalaxy(); }
  }

  D.agency = { open, close: shut, openProject, sync };
})();
