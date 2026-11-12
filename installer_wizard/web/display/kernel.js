(() => {
  const REPORT_MS = 5000, ID_OK = /^[A-Za-z0-9_.:@-]{1,96}$/, MB = 1048576;
  const st = { seen: new Map(), states: new Map(), engine: "local", nucleusOnly: false, observer: null, failed: new Set(), sending: false };

  const cardList = () => (window.NuxivaDesk && window.NuxivaDesk.cards ? window.NuxivaDesk.cards() : []);
  const visibleNow = (card) => !document.hidden && st.seen.get(card.el) === true && !card.el.classList.contains("hidden");

  function call(card, hook) {
    const fn = card.impl && card.impl[hook];
    if (typeof fn !== "function") return;
    try { fn.call(card.impl, card.el.firstChild); } catch (err) {
      st.failed.add(card.key);
      console.warn(`widget ${card.id} ${hook}:`, err);
    }
  }

  function apply(card, state) {
    if (st.states.get(card.key) === state) return;
    const before = st.states.get(card.key);
    st.states.set(card.key, state);
    card.el.classList.toggle("w-frozen", state === "frozen" || state === "hibernated" || state === "dormant");
    card.el.classList.toggle("w-hibernated", state === "hibernated" || state === "dormant");
    if (state === "live" && before && before !== "live") call(card, "resume");
    if (state !== "live" && (!before || before === "live")) call(card, "pause");
    window.dispatchEvent(new CustomEvent("nuxiva-widget-lifecycle", { detail: { key: card.key, id: card.id, state } }));
  }

  function localPass() {
    for (const card of cardList()) {
      const current = st.states.get(card.key);
      if (visibleNow(card)) apply(card, "live");
      else if (!current || current === "live") apply(card, "frozen");
    }
  }

  function observe() {
    if (!st.observer) return;
    for (const card of cardList()) {
      if (card.el.dataset.kernel) continue;
      card.el.dataset.kernel = "1";
      st.observer.observe(card.el);
    }
  }

  function declaredMb(inst) {
    const cost = inst && inst.cost;
    const gpu = cost && Number(cost.gpu);
    return Number.isFinite(gpu) && gpu > 0 ? gpu * 8 : 0;
  }

  function budgetMb() {
    const gpu = window.nuxivaGpu && window.nuxivaGpu.info;
    const memory = gpu && Number(gpu.device_memory);
    return Number.isFinite(memory) && memory > 0 ? memory * 1024 * 0.25 : null;
  }

  function payload() {
    const widgets = cardList().filter((c) => ID_OK.test(c.key) && ID_OK.test(c.id)).slice(0, 64).map((c) => ({
      instance: c.key, widget: c.id, refresh: Number(c.inst.refresh) || 0, visible: visibleNow(c),
      cost_mb: declaredMb(c.inst), failed: st.failed.has(c.key),
    }));
    const heap = performance.memory && performance.memory.usedJSHeapSize;
    return { screen: (window.NuxivaDesk && Number(window.NuxivaDesk.screen)) || 0, widgets, nucleus_only: st.nucleusOnly,
      budget_mb: budgetMb(), heap_mb: heap ? Math.round(heap / MB) : null };
  }

  async function report() {
    if (st.sending || document.hidden) return;
    st.sending = true;
    const body = payload();
    st.failed.clear();
    try {
      const res = await fetch("/api/display/lifecycle", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) throw new Error(`lifecycle ${res.status}`);
      const out = await res.json();
      st.engine = out.engine === "rust" ? "rust" : "local";
      const byKey = new Map(cardList().map((c) => [c.key, c]));
      for (const [key, state] of Object.entries(out.states || {})) {
        const card = byKey.get(key);
        if (card && state !== "live" && !visibleNow(card)) apply(card, state);
      }
    } catch (err) {
      st.engine = "local";
      console.warn("Display lifecycle report failed, local lifecycle only", err);
    } finally {
      st.sending = false;
    }
  }

  function start() {
    if ("IntersectionObserver" in window) {
      st.observer = new IntersectionObserver((entries) => {
        for (const e of entries) st.seen.set(e.target, e.isIntersecting);
        localPass();
      }, { threshold: 0.05 });
    }
    new MutationObserver(() => { observe(); localPass(); }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    document.addEventListener("visibilitychange", localPass);
    window.addEventListener("nuxiva:state", (ev) => {
      const away = !!(ev.detail && ev.detail.privacy && ev.detail.privacy.away);
      if (away !== st.nucleusOnly) { st.nucleusOnly = away; report(); }
    });
    observe();
    localPass();
    setInterval(report, REPORT_MS);
  }

  window.NuxivaKernel = { get engine() { return st.engine; }, state: (key) => st.states.get(key) || null };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
