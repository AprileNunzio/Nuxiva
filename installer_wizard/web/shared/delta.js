(function (global) {
  "use strict";

  const MAX_OPS = 4096;
  const WATCHDOG_MS = 25000;
  const RETRY_MS = 2000;

  class PatchError extends Error {}

  function tokens(path) {
    if (path === "") return [];
    if (typeof path !== "string" || path[0] !== "/") throw new PatchError("pointer");
    return path.slice(1).split("/").map((t) => {
      if (/~[^01]|~$/.test(t)) throw new PatchError("pointer");
      const token = t.replace(/~1/g, "/").replace(/~0/g, "~");
      if (FORBIDDEN.has(token)) throw new PatchError("pointer");
      return token;
    });
  }

  const FORBIDDEN = new Set(["__proto__", "constructor", "prototype"]);
  const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

  function applyOps(doc, ops) {
    if (!Array.isArray(ops) || ops.length > MAX_OPS) throw new PatchError("ops");
    let root = doc;
    for (const op of ops) {
      const path = tokens(op && op.path);
      if (!path.length) {
        if (op.op === "remove") throw new PatchError("root");
        root = op.value;
        continue;
      }
      const last = path.pop();
      let node = root;
      for (const t of path) {
        if (!isObject(node) || !Object.prototype.hasOwnProperty.call(node, t)) throw new PatchError("missing");
        node = node[t];
      }
      if (!isObject(node)) throw new PatchError("parent");
      if (op.op === "add") node[last] = op.value;
      else if (op.op === "replace" && Object.prototype.hasOwnProperty.call(node, last)) node[last] = op.value;
      else if (op.op === "remove" && Object.prototype.hasOwnProperty.call(node, last)) delete node[last];
      else throw new PatchError("op");
    }
    return root;
  }

  function withEvents(state, events) {
    const out = structuredClone(state);
    for (const e of Array.isArray(events) ? events : []) {
      if (e && e.k === "holo_action" && isObject(e.p)) out.holo_action = e.p;
    }
    return out;
  }

  function connectDelta(url, onState, onLink) {
    let es = null, retry = null, lastMsg = 0, state = null, version = -1;
    const emit = (events) => {
      const snapshot = withEvents(state, events);
      onState(snapshot);
      global.dispatchEvent(new CustomEvent("nuxiva:state", { detail: snapshot }));
    };
    const restart = () => {
      onLink && onLink(false);
      if (es) es.close();
      state = null; version = -1;
      clearTimeout(retry);
      retry = setTimeout(open, RETRY_MS);
    };
    function handle(frame) {
      if (frame.t === "ping") return;
      if (frame.t === "full") {
        state = frame.s; version = frame.v;
        emit(frame.e);
        return;
      }
      if (frame.t !== "patch" || state === null || frame.f !== version) throw new PatchError("version");
      state = applyOps(state, frame.p);
      version = frame.v;
      emit(frame.e);
    }
    function open() {
      es = new EventSource(url);
      es.onmessage = (ev) => {
        lastMsg = Date.now();
        onLink && onLink(true);
        try {
          handle(JSON.parse(ev.data));
        } catch (err) {
          console.error("Display stream frame rejected, resyncing", err);
          restart();
        }
      };
      es.onerror = restart;
    }
    open();
    setInterval(() => {
      if (lastMsg && Date.now() - lastMsg > WATCHDOG_MS) { lastMsg = 0; restart(); }
    }, 5000);
  }

  global.NuxivaDelta = { connectDelta, applyOps, PatchError };
})(typeof window !== "undefined" ? window : globalThis);
