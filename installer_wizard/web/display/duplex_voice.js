(() => {
  const D = window.NuxivaDisplay;
  const HEADER = 8, PCM_HEADER = 9, PCM_KIND = 1, MAX_RETRIES = 5, UNAVAILABLE = [1008, 1013];
  let ws = null, open = false, retries = 0, stream = null, chunks = new Map(), epoch = 0, pcmMode = false;

  function url() {
    return `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/voice/duplex/ws`;
  }

  function send(doc) {
    if (ws && open) ws.send(JSON.stringify(doc));
  }

  function onFrame(buffer) {
    if (!stream || buffer.byteLength <= PCM_HEADER) return;
    const view = new DataView(buffer);
    if (view.getUint8(0) !== PCM_KIND || view.getUint32(1) !== epoch) return;
    const seq = view.getUint32(5), meta = chunks.get(seq);
    if (!meta || meta.left <= 0) return;
    meta.left -= 1;
    const done = meta.left === 0 ? () => { chunks.delete(seq); send({ type: "played", gen: epoch, seq }); } : undefined;
    stream.addPcm(new Uint8Array(buffer, PCM_HEADER), meta.rate, done);
  }

  function onChunk(buffer) {
    if (pcmMode) return onFrame(buffer);
    if (!stream || buffer.byteLength <= HEADER) return;
    const view = new DataView(buffer), gen = view.getUint32(0), seq = view.getUint32(4);
    stream.add(buffer.slice(HEADER), () => send({ type: "played", gen, seq }));
  }

  function onText(raw) {
    let ev;
    try { ev = JSON.parse(raw); } catch (_) { return; }
    if (!ev || typeof ev !== "object") return;
    if (ev.type === "chunk" && ev.pcm === true) {
      if (ev.gen === epoch && Number.isInteger(ev.seq) && Number.isInteger(ev.rate) && Number.isInteger(ev.frames) && ev.frames > 0 && ev.frames <= 4096 && ev.rate >= 8000 && ev.rate <= 48000) {
        pcmMode = true;
        chunks.set(ev.seq, { rate: ev.rate, left: ev.frames });
      }
    } else if (ev.type === "reply_start") {
      epoch = Number.isInteger(ev.gen) ? ev.gen : 0;
      chunks = new Map();
      pcmMode = false;
      stream = D.voiceServerStream();
      if (D.Ear) D.Ear.speaking(true);
    } else if (ev.type === "reply_end") {
      const closing = stream;
      stream = null;
      if (closing) closing.close().finally(() => { if (D.Ear) D.Ear.speaking(false); });
    } else if (ev.type === "cut") {
      stream = null;
      chunks = new Map();
      D.voiceStop();
      if (D.Ear) D.Ear.speaking(false);
    }
  }

  function connect() {
    if (ws) return;
    try { ws = new WebSocket(url()); } catch (_) { return; }
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      open = true; retries = 0;
      ws.send(JSON.stringify({ type: "hello", version: 1, pcm: typeof D.voiceServerStream === "function" }));
    };
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
