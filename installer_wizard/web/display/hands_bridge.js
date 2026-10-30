(() => {
  const RETRY_MS = 5000, CONTEXT_RE = /^[a-z0-9_.-]{1,64}$/;

  const side = (entry) => {
    const label = entry && entry[0] && (entry[0].categoryName || entry[0].displayName);
    return label === "Left" ? "left" : label === "Right" ? "right" : "unknown";
  };
  const score = (entry) => {
    const value = entry && entry[0] && entry[0].score;
    return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 1;
  };

  function create(handlers) {
    let socket = null, open = false, closed = false, context = "desktop";

    function connect() {
      if (closed) return;
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${scheme}://${location.host}/api/hands/ws?context=${encodeURIComponent(context)}`);
      socket.onopen = () => { open = true; handlers.status(true); };
      socket.onclose = () => { open = false; handlers.status(false); if (!closed) setTimeout(connect, RETRY_MS); };
      socket.onerror = () => { };
      socket.onmessage = (message) => {
        let events;
        try { events = JSON.parse(message.data); } catch (err) { return; }
        if (Array.isArray(events)) events.forEach((event) => { if (event && typeof event.type === "string") handlers.event(event); });
      };
    }

    function send(now, result) {
      if (!open || socket.readyState !== WebSocket.OPEN) return false;
      const sides = result.handedness || result.handednesses || [];
      const hands = (result.landmarks || []).slice(0, 4).map((points, i) => ({
        handedness: side(sides[i]), score: score(sides[i]), points: points.map((p) => [p.x, p.y, p.z || 0]),
      }));
      socket.send(JSON.stringify({ t: Math.max(0, Math.round(now)), hands }));
      return true;
    }

    function setContext(next) {
      if (!CONTEXT_RE.test(next) || next === context) return;
      context = next;
      if (open) socket.send(JSON.stringify({ context }));
    }

    connect();
    return { send, setContext, get ready() { return open; }, close() { closed = true; if (socket) socket.close(); } };
  }

  window.NuxivaHandsBridge = { create };
})();
