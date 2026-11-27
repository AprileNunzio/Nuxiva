(() => {
  const D = window.NuxivaDisplay;
  const GAP_MS = 600, MAX_TEXT = 400;
  let last = "", sentAt = 0;

  function post(body) {
    fetch("/api/assistant/anticipate", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Client": D.clientId || "" },
      body: JSON.stringify(body),
    }).catch((err) => console.warn("Anticipo non inviato", err));
  }

  D.Anticipate = {
    event(ev) {
      if (!ev || typeof ev !== "object" || ev.origin === false) return;
      if (ev.type === "wake") { post({}); return; }
      if (ev.type !== "partial" || !ev.addressed || typeof ev.text !== "string") return;
      const text = ev.text.trim().slice(0, MAX_TEXT);
      if (!text || text === last || Date.now() - sentAt < GAP_MS) return;
      last = text;
      sentAt = Date.now();
      post({ text });
    },
  };
})();
