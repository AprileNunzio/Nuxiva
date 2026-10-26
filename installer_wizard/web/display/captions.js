(() => {
  const D = window.NuxivaDisplay;
  const T = window.PageText ? PageText.scope("web/display") : (key) => key;
  const DEFAULTS = { enabled: true, scope: "all", speaker: true, size: "medium", hold: 6, position: "bottom" };
  const SIZES = ["small", "medium", "large"];
  const POSITIONS = ["bottom", "center"];
  const MAX_LINES = 3;
  const STALE_MS = 20000;
  const RELOAD_MS = 60000;
  const SLUG = /^[a-z0-9][a-z0-9-]{0,40}$/;
  const lines = new Map();
  let cfg = { ...DEFAULTS };
  let names = {};
  let canIdentify = false;

  const root = document.createElement("div");
  root.id = "live-captions";
  root.setAttribute("role", "log");
  root.setAttribute("aria-live", "polite");
  document.body.appendChild(root);

  function sanitize(raw) {
    const c = raw && typeof raw === "object" ? raw : {};
    const hold = Number(c.hold);
    return {
      enabled: c.enabled !== false,
      scope: c.scope === "addressed" ? "addressed" : "all",
      speaker: c.speaker !== false,
      size: SIZES.includes(c.size) ? c.size : DEFAULTS.size,
      hold: Number.isFinite(hold) ? Math.max(2, Math.min(30, hold)) : DEFAULTS.hold,
      position: POSITIONS.includes(c.position) ? c.position : DEFAULTS.position,
    };
  }

  function apply() {
    root.dataset.size = cfg.size;
    root.dataset.position = cfg.position;
    root.hidden = !cfg.enabled;
    document.body.classList.toggle("has-captions", cfg.enabled);
    if (!cfg.enabled) clearAll();
  }

  async function load() {
    try {
      const r = await fetch("/api/ear/config", { cache: "no-store" });
      if (!r.ok) return;
      const data = await r.json();
      cfg = sanitize(data.captions);
      names = data.speakers && typeof data.speakers === "object" ? data.speakers : {};
      apply();
    } catch (e) { console.warn("Impostazioni dei sottotitoli non lette, uso quelle predefinite", e); }
  }

  function hue(slug) {
    let h = 0;
    for (const ch of slug) h = (h * 31 + ch.charCodeAt(0)) % 360;
    return h;
  }

  function label(entry, ev) {
    const slug = typeof ev.speaker === "string" && SLUG.test(ev.speaker) ? ev.speaker : "";
    if (!cfg.speaker) { entry.who.hidden = true; return; }
    if (!slug && !(canIdentify && entry.final)) { entry.who.hidden = true; return; }
    entry.who.hidden = false;
    entry.who.textContent = slug ? (typeof names[slug] === "string" ? names[slug] : slug) : T("cap_unknown");
    entry.el.style.setProperty("--cap-hue", slug ? String(hue(slug)) : "215");
    entry.el.classList.toggle("unknown", !slug);
  }

  function remove(utt) {
    const entry = lines.get(utt);
    if (!entry) return;
    lines.delete(utt);
    clearTimeout(entry.timer);
    entry.el.classList.add("out");
    setTimeout(() => entry.el.remove(), 700);
  }

  function clearAll() {
    [...lines.keys()].forEach(remove);
  }

  function expire(entry, ms) {
    clearTimeout(entry.timer);
    entry.timer = setTimeout(() => remove(entry.utt), ms);
  }

  function open(utt, addressed) {
    if (lines.has(utt)) return lines.get(utt);
    while (lines.size >= MAX_LINES) remove(lines.keys().next().value);
    const el = document.createElement("div");
    el.className = "cap";
    const who = document.createElement("span");
    who.className = "cap-who";
    who.hidden = true;
    const text = document.createElement("span");
    text.className = "cap-text";
    el.append(who, text);
    root.appendChild(el);
    const entry = { utt, el, who, text, spans: [], final: false, timer: 0 };
    lines.set(utt, entry);
    expire(entry, STALE_MS);
    el.classList.toggle("addressed", !!addressed);
    return entry;
  }

  function words(entry, list, stable) {
    list.forEach((word, i) => {
      let span = entry.spans[i];
      if (!span) {
        span = document.createElement("span");
        span.className = "cap-w in";
        entry.text.appendChild(span);
        entry.spans.push(span);
      }
      if (span.dataset.w !== word) {
        span.dataset.w = word;
        span.textContent = `${word} `;
      }
      span.classList.toggle("stable", i < stable);
    });
    while (entry.spans.length > list.length) entry.spans.pop().remove();
  }

  function visible(addressed) {
    return cfg.enabled && (cfg.scope === "all" || addressed);
  }

  function partial(ev) {
    if (typeof ev.utt !== "string" || typeof ev.text !== "string" || !visible(ev.addressed)) return;
    const entry = open(ev.utt, ev.addressed);
    entry.el.classList.toggle("addressed", !!ev.addressed);
    words(entry, ev.text.split(/\s+/).filter(Boolean), Number(ev.stable) || 0);
    label(entry, ev);
    expire(entry, STALE_MS);
  }

  function settle(ev, addressed) {
    if (typeof ev.text !== "string" || !ev.text.trim() || !visible(addressed)) { if (ev.utt) remove(ev.utt); return; }
    const entry = open(typeof ev.utt === "string" && ev.utt ? ev.utt : `f${Date.now()}`, addressed);
    entry.final = true;
    entry.el.classList.toggle("addressed", addressed);
    entry.el.classList.add("done");
    const list = ev.text.split(/\s+/).filter(Boolean);
    words(entry, list, list.length);
    label(entry, ev);
    expire(entry, cfg.hold * 1000);
  }

  function event(ev) {
    if (!ev || typeof ev !== "object") return;
    if (ev.type === "partial") partial(ev);
    else if (ev.type === "heard") settle(ev, false);
    else if (ev.type === "transcript") settle(ev, true);
    else if (ev.type === "caption_drop" && typeof ev.utt === "string") remove(ev.utt);
    else if (ev.type === "ready") canIdentify = !!ev.voiceprint;
  }

  window.addEventListener("pagehide", clearAll);
  if (window.PageText) PageText.onChange(() => lines.forEach((entry) => { if (!entry.who.hidden && entry.el.classList.contains("unknown")) entry.who.textContent = T("cap_unknown"); }));
  apply();
  load();
  setInterval(load, RELOAD_MS);
  D.Captions = Object.freeze({ event, reload: load });
})();
