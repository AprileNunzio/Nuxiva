(() => {
  const D = window.NuxivaDisplay;
  const HEADER = 8, MAX_RETRIES = 5, UNAVAILABLE = [1008, 1013];
  let ws = null, open = false, retries = 0, stream = null;

  function url() {
    return `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/voice/duplex/ws`;
  }

  function send(doc) {
    if (ws && open) ws.send(JSON.stringify(doc));
  }

  function onChunk(buffer) {
    if (!stream || buffer.byteLength <= HEADER) return;
    const view = new DataView(buffer), gen = view.getUint32(0), seq = view.getUint32(4);
    stream.add(buffer.slice(HEADER), () => send({ type: "played", gen, seq }));
  }

  function onText(raw) {
    let ev;
    try { ev = JSON.parse(raw); } catch (_) { return; }
    if (!ev || typeof ev !== "object") return;
    if (ev.type === "reply_start") {
      stream = D.voiceServerStream();
      if (D.Ear) D.Ear.speaking(true);
    } else if (ev.type === "reply_end") {
      const closing = stream;
      stream = null;
      if (closing) closing.close().finally(() => { if (D.Ear) D.Ear.speaking(false); });
    } else if (ev.type === "cut") {
      stream = null;
      D.voiceStop();
      if (D.Ear) D.Ear.speaking(false);
    }
  }

  function connect() {
    if (ws) return;
    try { ws = new WebSocket(url()); } catch (_) { return; }
    ws.binaryType = "arraybuffer";
    ws.onopen = () => { open = true; retries = 0; };
    ws.onmessage = (e) => (typeof e.data === "string" ? onText(e.data) : onChunk(e.data));
    ws.onclose = (e) => {
      open = false; ws = null; stream = null;
      if (UNAVAILABLE.includes(e.code) || retries >= MAX_RETRIES) return;
      retries += 1;
      setTimeout(connect, Math.min(30000, 2000 * retries * retries));
    };
    ws.onerror = () => {};
  }

  D.DuplexVoice = {
    connected: () => open,
    cut: () => send({ type: "cut" }),
  };

  connect();
})();
