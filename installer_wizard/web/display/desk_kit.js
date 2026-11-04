(() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const LOCALES = { it: "it-IT", en: "en-GB", es: "es-ES", fr: "fr-FR" };
  const lang = () => (LOCALES[String(document.documentElement.lang || "").slice(0, 2)] ? String(document.documentElement.lang).slice(0, 2) : "it");
  const locale = () => LOCALES[lang()];
  const plain = (v, max = 6000) => {
    const s = String(v ?? "").slice(0, max).replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|div|li|tr|h[1-6])>/gi, "\n");
    return s.includes("<") ? new DOMParser().parseFromString(s, "text/html").body.textContent : s;
  };
  const lines = (v, max = 10, size = 6000) => plain(v, size).split("\n").map((l) => l.trim()).filter(Boolean).slice(0, max);
  const pair = (line, size = 48) => line.match(new RegExp(`^([^:]{1,${size}}):\\s+(.+)$`));
  const str = (v, max = 400) => (typeof v === "string" ? v : typeof v === "number" && Number.isFinite(v) ? String(v) : "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim().slice(0, max);
  const num = (v) => {
    const n = typeof v === "string" && v.trim() ? Number(v.trim().replace(",", ".")) : v;
    return typeof n === "number" && Number.isFinite(n) ? n : null;
  };
  const arr = (v, max = 50) => (Array.isArray(v) ? v.slice(0, max) : []);
  const pick = (o, keys, max = 400) => {
    if (!o || typeof o !== "object") return "";
    for (const k of keys) { const s = Object.hasOwn(o, k) ? str(o[k], max) : ""; if (s) return s; }
    return "";
  };
  const stamp = (v) => {
    const n = num(v);
    if (n !== null) return n > 0 ? (n > 1e12 ? n / 1000 : n) : null;
    const t = typeof v === "string" ? Date.parse(v) : NaN;
    return Number.isFinite(t) ? t / 1000 : null;
  };
  const intl = new Map();
  const cached = (kind, opts) => {
    const k = `${kind}|${locale()}|${JSON.stringify(opts || {})}`;
    if (!intl.has(k)) intl.set(k, kind === "n" ? new Intl.NumberFormat(locale(), opts) : kind === "r" ? new Intl.RelativeTimeFormat(locale(), opts) : new Intl.DateTimeFormat(locale(), opts));
    return intl.get(k);
  };
  const fmt = (v, opts) => { const n = num(v); return n === null ? "" : cached("n", opts).format(n); };
  const when = (v, opts = { hour: "2-digit", minute: "2-digit" }) => { const s = stamp(v); return s === null ? "" : cached("d", opts).format(new Date(s * 1000)); };
  const ago = (v) => {
    const s = stamp(v);
    if (s === null) return "";
    const d = s - Date.now() / 1000, a = Math.abs(d);
    const [n, unit] = a < 10 ? [0, "second"] : a < 50 ? [d, "second"] : a < 3000 ? [d / 60, "minute"] : a < 72000 ? [d / 3600, "hour"] : [d / 86400, "day"];
    return cached("r", { numeric: "auto", style: "short" }).format(Math.round(n), unit);
  };
  const copy = async (text) => {
    const value = String(text ?? "");
    try {
      if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(value); return true; }
    } catch (_) {}
    const area = document.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
    area.remove();
    return ok;
  };
  window.NuxivaDeskKit = Object.freeze({ esc, lang, locale, plain, lines, pair, str, num, arr, pick, stamp, fmt, when, ago, copy });
})();
