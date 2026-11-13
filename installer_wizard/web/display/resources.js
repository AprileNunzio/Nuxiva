(() => {
  const ID_OK = /^[a-z0-9_.:-]{1,64}$/;
  const DEVICE_KEY = "nuxiva-device";
  const REPORT_EVERY = 15000, SETTLE = 250, MAX_SURFACES = 64;
  const COVER_CLASSES = Object.freeze(["agency-open", "desk-full"]);
  const surfaces = new Map();
  const claims = new Set();
  const st = { level: "calm", hibernate: new Set(), timer: 0, fails: 0, lastReport: 0 };

  const device = () => {
    try {
      const value = localStorage.getItem(DEVICE_KEY);
      return /^[A-Za-z0-9_-]{6,40}$/.test(value || "") ? value : "";
    } catch (err) { return ""; }
  };

  const covered = () => document.hidden || claims.size > 0 || COVER_CLASSES.some((c) => document.body.classList.contains(c));

  const call = (surface, name) => {
    const fn = surface.spec[name];
    if (typeof fn !== "function") return;
    try { fn(); } catch (err) { console.error(`Risorse: ${name} di ${surface.spec.id} non riuscito`, err); }
  };

  function wanted(surface) {
    if (surface.spec.cls === "protected") return "active";
    if (surface.spec.coverable !== false && covered()) return "suspended";
    return "active";
  }

  function apply(surface, next, now) {
    if (surface.state === next) return;
    surface.state = next;
    if (next === "active") {
      surface.idleFrom = 0;
      surface.released = false;
      call(surface, "resume");
      return;
    }
    surface.idleFrom = now;
    call(surface, "suspend");
  }

  function sync() {
    clearTimeout(st.timer);
    st.timer = 0;
    const now = performance.now();
    let later = false;
    for (const surface of surfaces.values()) {
      const next = wanted(surface);
      if (next === "active") apply(surface, next, now);
      else if (surface.state !== "suspended") later = true;
    }
    if (later) st.timer = setTimeout(settle, SETTLE);
    release(now);
  }

  function settle() {
    st.timer = 0;
    const now = performance.now();
    for (const surface of surfaces.values()) apply(surface, wanted(surface), now);
    release(now);
  }

  function release(now) {
    for (const surface of surfaces.values()) {
      if (surface.state !== "suspended" || surface.released || !st.hibernate.has(surface.spec.id)) continue;
      surface.released = true;
      call(surface, "release");
    }
  }

  function register(spec) {
    if (!spec || !ID_OK.test(spec.id || "") || surfaces.size >= MAX_SURFACES) return null;
    const surface = { spec, state: "active", idleFrom: 0, released: false };
    surfaces.set(spec.id, surface);
    sync();
    return Object.freeze({ id: spec.id, unregister: () => { surfaces.delete(spec.id); } });
  }

  function claim(id) { if (ID_OK.test(id || "")) { claims.add(id); sync(); } }
  function drop(id) { if (claims.delete(id)) sync(); }

  function megabytes(surface) {
    try {
      const value = typeof surface.spec.mb === "function" ? Number(surface.spec.mb()) : Number(surface.spec.mb);
      return Number.isFinite(value) ? Math.min(65536, Math.max(0, value)) : 0;
    } catch (err) {
      console.error(`Risorse: misura di ${surface.spec.id} non riuscita`, err);
      return 0;
    }
  }

  function setLevel(level) {
    if (!["calm", "elevated", "high", "critical"].includes(level) || level === st.level) return;
    st.level = level;
    const heavy = level === "high" || level === "critical";
    document.body.classList.toggle("res-pressure", heavy);
    if (window.nuxivaPerf) {
      if (heavy) window.nuxivaPerf.lite(`governatore: risorse ${level}`);
      else if (window.nuxivaPerf.relax) window.nuxivaPerf.relax();
    }
    window.dispatchEvent(new CustomEvent("nuxiva-resource-level", { detail: level }));
  }

  function directive(data) {
    if (!data || typeof data !== "object") return;
    setLevel(data.level);
    st.hibernate = new Set((Array.isArray(data.hibernate) ? data.hibernate : []).filter((id) => ID_OK.test(id)).slice(0, MAX_SURFACES));
    release(performance.now());
  }

  async function report() {
    const id = device();
    if (!id || document.hidden || st.fails > 5) return;
    const now = performance.now();
    const list = [...surfaces.values()].map((s) => ({
      id: s.spec.id, mb: Math.round(megabytes(s) * 10) / 10, visible: s.state === "active" && !covered(),
      idle_ms: s.idleFrom ? Math.round(now - s.idleFrom) : 0,
    }));
    const memory = performance.memory;
    const body = { device: id, surfaces: list, js_heap_mb: memory ? Math.round(memory.usedJSHeapSize / 1048576) : 0,
      cores: navigator.hardwareConcurrency || 0, device_memory: navigator.deviceMemory || 0 };
    try {
      const r = await fetch("/api/resources/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!r.ok) { st.fails++; return; }
      st.fails = 0;
      directive(await r.json());
    } catch (err) { st.fails++; }
  }

  function snapshot() {
    return [...surfaces.values()].map((s) => ({ id: s.spec.id, state: s.state, released: s.released, mb: megabytes(s) }));
  }

  new MutationObserver(sync).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  document.addEventListener("visibilitychange", sync);
  setInterval(report, REPORT_EVERY);
  setTimeout(report, 4000);
  window.NuxivaResources = Object.freeze({
    register, claim, release: drop, report, snapshot, sync,
    get covered() { return covered(); },
    get level() { return st.level; },
  });
})();
