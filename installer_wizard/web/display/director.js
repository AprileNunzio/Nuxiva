(() => {
  const D = window.NuxivaDisplay;
  const STATES = new Set(["shown", "min", "hidden"]);
  const REFRESH = 4000;
  const MAX_BACKOFF = 60000;
  let plan = null;
  let sig = "";
  let timer = 0;
  let inflight = false;
  let again = false;
  let failures = 0;
  let nextAt = 0;
  let vetoSig = "";
  const asked = new Set();

  const body = document.body;
  const input = () => document.getElementById("in");
  const dock = () => document.querySelector(".dock");

  function context() {
    const s = D.state || {};
    const pr = s.presence;
    const people = pr && pr.status === "ok" && Array.isArray(pr.people) ? pr.people.length : 0;
    const np = s.now_playing;
    const desk = window.NuxivaDesk ? [...new Set((window.NuxivaDesk.candidates || []).map((i) => i && i.id).filter((id) => typeof id === "string"))] : [];
    const field = input();
    const project = document.getElementById("project-widget");
    return {
      mode: ["face", "brain", "focus", "flow"].includes(D.mode) ? D.mode : "face",
      listening: body.classList.contains("listening") || body.classList.contains("transcribing"),
      conversing: body.classList.contains("conversing"),
      typing: !!(field && (document.activeElement === field || field.value.trim())) || !!(dock() && dock().classList.contains("expanded")),
      speaking: typeof D.isSpeaking === "function" ? !!D.isSpeaking() : false,
      people,
      desk: desk.slice(0, 40).sort(),
      music: !!(np && (np.title || np.artist)),
      project: !!(project && !project.hidden),
    };
  }

  function stateOf(id) {
    const entry = plan && plan.surfaces && plan.surfaces[id];
    return entry && STATES.has(entry.state) ? entry.state : null;
  }

  function apply() {
    document.querySelectorAll("[data-surface]").forEach((el) => {
      const st = stateOf(el.dataset.surface);
      if (st) el.dataset.stage = st;
      else delete el.dataset.stage;
    });
    const chat = stateOf("chat");
    if (chat) body.dataset.stageChat = chat;
    else delete body.dataset.stageChat;
    const vetoed = plan ? Object.keys(plan.surfaces).filter((k) => k.startsWith("w:") && stateOf(k) === "hidden").sort().join(" ") : "";
    if (vetoed !== vetoSig && window.NuxivaDesk && window.NuxivaDesk.setVeto) {
      vetoSig = vetoed;
      const hide = new Set(vetoed.split(" ").filter(Boolean));
      window.NuxivaDesk.setVeto(hide.size ? (item) => hide.has(`w:${item.id}`) : null);
    }
    window.dispatchEvent(new CustomEvent("nuxiva-stage"));
  }

  function reset() {
    plan = null;
    apply();
  }

  function valid(data) {
    if (!data || typeof data !== "object" || typeof data.context_key !== "string" || !data.surfaces || typeof data.surfaces !== "object") return false;
    return Object.values(data.surfaces).every((v) => v && STATES.has(v.state));
  }

  async function request() {
    if (inflight) { again = true; return; }
    if (Date.now() < nextAt || !D.clientId) return;
    inflight = true;
    const ctx = context();
    sig = JSON.stringify(ctx);
    try {
      const r = await fetch("/api/stage/plan", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
        body: JSON.stringify({ client: D.clientId, context: ctx }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      if (!valid(data)) throw new TypeError("piano non valido");
      const changed = !plan || plan.context_key !== data.context_key;
      plan = data;
      failures = 0;
      if (changed) asked.clear();
      apply();
    } catch (err) {
      failures += 1;
      nextAt = Date.now() + Math.min(MAX_BACKOFF, 2000 * 2 ** Math.min(failures, 5));
      if (plan) reset();
      if (failures === 1) console.info("Regista non disponibile, interfaccia completa:", err.message);
    } finally {
      inflight = false;
      if (again) { again = false; poke(); }
    }
  }

  function poke() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (JSON.stringify(context()) !== sig || !plan) request();
    }, 150);
  }

  function feedback(surface, wanted) {
    if (!plan || asked.has(surface)) return;
    asked.add(surface);
    fetch("/api/stage/feedback", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
      body: JSON.stringify({ client: D.clientId, surface, wanted }),
    }).catch(() => {});
  }

  function start() {
    new MutationObserver(poke).observe(body, { attributes: true, attributeFilter: ["class"] });
    const d = dock();
    if (d) new MutationObserver(() => {
      if (d.classList.contains("expanded") && stateOf("chat") === "min") feedback("chat", true);
      poke();
    }).observe(d, { attributes: true, attributeFilter: ["class"] });
    const field = input();
    if (field) ["focus", "blur", "input"].forEach((ev) => field.addEventListener(ev, poke, { passive: true }));
    const project = document.getElementById("project-widget");
    if (project) new MutationObserver(poke).observe(project, { attributes: true, attributeFilter: ["hidden"] });
    document.addEventListener("pointerdown", (ev) => {
      const el = ev.target instanceof Element ? ev.target.closest("[data-surface][data-stage='min']") : null;
      if (el) feedback(el.dataset.surface, true);
    }, { passive: true, capture: true });
    setInterval(() => { if (!document.hidden) request(); }, REFRESH);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) request(); });
    request();
  }

  D.Director = Object.freeze({ start, poke, state: stateOf, get plan() { return plan; } });
})();
