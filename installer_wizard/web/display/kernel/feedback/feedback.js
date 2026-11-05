(() => {
  const FLUSH_MS = 4000, THROTTLE_MS = 5000, MAX_BATCH = 32;
  const queue = new Map(), last = new Map();

  const widgetKey = (el) => {
    const card = el && el.closest ? el.closest(".desk > .widget") : null;
    return card && card.dataset.key ? card.dataset.key : "";
  };

  function note(target, kind) {
    const key = widgetKey(target), now = Date.now();
    if (!key || now - (last.get(key) || 0) < THROTTLE_MS) return;
    last.set(key, now);
    if (queue.size < MAX_BATCH) queue.set(key, kind);
  }

  function flush(keepalive) {
    if (!queue.size) return;
    const events = [...queue].map(([key, kind]) => ({ key, kind }));
    queue.clear();
    fetch("/api/display/feedback", { method: "POST", credentials: "same-origin", keepalive: !!keepalive,
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" }, body: JSON.stringify({ events }) })
      .then((r) => { if (!r.ok) throw new Error(`errore ${r.status}`); })
      .catch((e) => console.warn("Segnali di apprendimento non inviati:", e.message));
  }

  document.addEventListener("pointerdown", (e) => note(e.target, "interact"), { capture: true, passive: true });
  document.addEventListener("wheel", (e) => note(e.target, "interact"), { capture: true, passive: true });
  document.addEventListener("nuxiva-gesture", (e) => note(e.target, "dwell"), { capture: true, passive: true });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") flush(true); });
  setInterval(() => flush(false), FLUSH_MS);
})();
