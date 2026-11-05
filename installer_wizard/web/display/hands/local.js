(() => {
  const BASE = "/static/display/hands/wasm/";
  const V = window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : "";
  const PROFILE_MS = 30000, SCENE_MS = 1000, EVENTS_MS = 2000, MAX_BATCH = 32, CONTEXT_RE = /^[a-z0-9_.-]{1,64}$/;
  const NOTABLE = new Set(["gesture", "action"]);

  const side = (entry) => {
    const label = entry && entry[0] && (entry[0].categoryName || entry[0].displayName);
    return label === "Left" ? "left" : label === "Right" ? "right" : "unknown";
  };
  const score = (entry) => {
    const value = entry && entry[0] && entry[0].score;
    return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 1;
  };

  async function getJson(url) {
    const r = await fetch(url, { credentials: "same-origin", cache: "no-store", headers: { "X-Nuxiva-Request": "1" } });
    if (!r.ok) throw new Error(`${url}: errore ${r.status}`);
    return r.json();
  }

  function postEvents(events) {
    return fetch("/api/hands/display/events", { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" }, body: JSON.stringify({ events }) })
      .then((r) => { if (!r.ok) throw new Error(`errore ${r.status}`); })
      .catch((e) => console.warn("Mani: eventi non registrati sul server:", e.message));
  }

  function available() {
    return typeof wasm_bindgen === "function" && typeof WebAssembly === "object";
  }

  function create(handlers) {
    let engine = null, revision = -1, context = "desktop", closed = false, seen = 0;
    const outbox = [], timers = [];

    async function refreshProfile() {
      const data = await getJson("/api/hands/display/profile");
      if (data.revision === revision || !engine) return;
      engine.setProfile(JSON.stringify(data.profile || {}));
      revision = data.revision;
    }

    async function refreshScene() {
      if (!engine || performance.now() - seen > 5000) return;
      const data = await getJson("/api/hands/display/scene");
      engine.setScene(JSON.stringify(data.faces || []), String(data.audience || "uncertain"), !!data.trust_guests);
    }

    function every(ms, task, label) {
      timers.push(setInterval(() => { task().catch((e) => console.warn(`Mani: ${label} non aggiornato:`, e.message)); }, ms));
    }

    async function boot() {
      await wasm_bindgen({ module_or_path: `${BASE}hands_core_bg.wasm${V}` });
      const data = await getJson("/api/hands/display/profile");
      engine = new wasm_bindgen.WasmHands(JSON.stringify(data.profile || {}));
      revision = data.revision;
      seen = performance.now();
      await refreshScene();
      every(PROFILE_MS, refreshProfile, "profilo gesti");
      every(SCENE_MS, refreshScene, "riconoscimento delle mani");
      timers.push(setInterval(() => { if (outbox.length) postEvents(outbox.splice(0, MAX_BATCH)); }, EVENTS_MS));
      handlers.status(true);
    }

    function send(now, result) {
      if (!engine || closed) return false;
      const sides = result.handedness || result.handednesses || [];
      const hands = (result.landmarks || []).slice(0, 4).map((points, i) => ({
        handedness: side(sides[i]), score: score(sides[i]), points: points.map((p) => [p.x, p.y, p.z || 0]),
      }));
      if (hands.length) seen = performance.now();
      let events;
      try { events = JSON.parse(engine.feed(JSON.stringify({ t: Math.max(0, Math.round(now)), hands }), context)); }
      catch (e) { console.warn("Mani: fotogramma scartato dal motore WASM:", e.message || e); return true; }
      for (const event of events) {
        handlers.event(event);
        if (NOTABLE.has(event.type) && outbox.length < MAX_BATCH * 4) outbox.push(event);
      }
      return true;
    }

    function setContext(next) {
      if (CONTEXT_RE.test(next)) context = next;
    }

    function close() {
      closed = true;
      timers.forEach(clearInterval);
      if (engine) engine.free();
      engine = null;
    }

    boot().catch((e) => {
      console.error("Mani: motore WASM non avviato, uso il canale del server:", e.message || e);
      close();
      handlers.status(false);
      if (handlers.fallback) handlers.fallback();
    });
    return { send, setContext, close, get ready() { return !!engine && !closed; }, kind: "wasm" };
  }

  window.NuxivaHandsLocal = { create, available };
})();
