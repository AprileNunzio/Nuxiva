(() => {
  const loaded = {};
  const load = (src) => loaded[src] || (loaded[src] = new Promise((ok, fail) => {
    const s = document.createElement("script");
    s.src = src; s.onload = ok; s.onerror = () => fail(new Error(`libreria ${src} non disponibile`));
    document.head.appendChild(s);
  }));

  async function asHls(video, src) {
    const native = () => { video.src = src; return { destroy() { video.removeAttribute("src"); video.load(); } }; };
    try { await load("/vendor/hls.min.js"); } catch (err) { if (video.canPlayType("application/vnd.apple.mpegurl")) return native(); throw err; }
    if (!window.Hls || !window.Hls.isSupported()) {
      if (video.canPlayType("application/vnd.apple.mpegurl")) return native();
      throw new Error("HLS non supportato");
    }
    const hls = new window.Hls({ lowLatencyMode: true, backBufferLength: 30 });
    hls.loadSource(src); hls.attachMedia(video);
    return new Promise((ok, fail) => {
      hls.on(window.Hls.Events.MANIFEST_PARSED, () => ok(hls));
      hls.on(window.Hls.Events.ERROR, (_, data) => { if (data.fatal) { hls.destroy(); fail(new Error(data.details || "errore HLS")); } });
    });
  }

  async function asTs(video, src) {
    await load("/vendor/mpegts.js");
    if (!window.mpegts || !window.mpegts.isSupported()) throw new Error("flusso TS non supportato");
    const player = window.mpegts.createPlayer({ type: "mpegts", isLive: true, url: new URL(src, location.href).href }, { enableWorker: true, liveBufferLatencyChasing: true });
    player.attachMediaElement(video); player.load();
    return player;
  }

  async function asDash(video, src) {
    await load("/vendor/dash.all.min.js");
    const dash = window.dashjs;
    if (!dash || !dash.MediaPlayer || (typeof dash.supportsMediaSource === "function" && !dash.supportsMediaSource())) throw new Error("DASH non supportato");
    const player = dash.MediaPlayer().create();
    const events = dash.MediaPlayer.events;
    player.updateSettings({ debug: { logLevel: dash.Debug ? dash.Debug.LOG_LEVEL_NONE : 0 }, streaming: { buffer: { fastSwitchEnabled: true } } });
    return new Promise((ok, fail) => {
      let settled = false;
      player.on(events.STREAM_INITIALIZED, () => { if (!settled) { settled = true; ok({ destroy() { player.reset(); } }); } });
      player.on(events.ERROR, (e) => {
        if (settled) return;
        settled = true;
        try { player.reset(); } catch {}
        fail(new Error((e && e.error && (e.error.message || e.error.code)) || "errore DASH"));
      });
      player.initialize(video, new URL(src, location.href).href, false);
    });
  }

  const PLAYERS = { hls: asHls, dash: asDash, ts: asTs };
  const ORDER = { hls: ["hls", "dash", "ts"], dash: ["dash", "hls", "ts"], ts: ["ts", "hls", "dash"], "": ["hls", "dash", "ts"] };

  async function sniff(src) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 6000);
    try {
      const res = await fetch(src, { signal: ctl.signal, cache: "no-store", credentials: "same-origin", referrerPolicy: "no-referrer" });
      if (!res.ok) return "";
      const type = (res.headers.get("content-type") || "").toLowerCase();
      if (type.includes("dash+xml")) return "dash";
      if (type.includes("mpegurl")) return "hls";
      if (type.includes("mp2t")) return "ts";
      const reader = res.body && res.body.getReader();
      const chunk = reader ? (await reader.read()).value : null;
      if (!chunk || !chunk.length) return "";
      if (chunk[0] === 0x47) return "ts";
      const head = new TextDecoder().decode(chunk.subarray(0, 1024)).replace(/^\uFEFF/, "").trimStart();
      if (head.startsWith("#EXTM3U")) return "hls";
      if (/<(?:[\w-]+:)?MPD[\s>]/.test(head)) return "dash";
      return "";
    } catch { return ""; }
    finally { clearTimeout(timer); ctl.abort(); }
  }

  async function play(video, src, onState) {
    const say = (s) => onState && onState(s);
    say("loading");
    let handle = null;
    const errors = [];
    for (const kind of ORDER[await sniff(src)] || ORDER[""]) {
      try { handle = await PLAYERS[kind](video, src); break; }
      catch (err) { errors.push(err.message); }
    }
    if (!handle) { say("error"); throw new Error(errors.join(" · ")); }
    video.muted = false;
    try { await video.play(); } catch { video.muted = true; await video.play().catch(() => say("blocked")); }
    say("playing");
    return { stop() { try { handle.destroy(); } catch { video.pause(); } } };
  }

  window.NuxivaTv = { play };
})();
