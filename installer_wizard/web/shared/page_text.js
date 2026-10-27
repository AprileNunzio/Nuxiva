(function (global) {
  "use strict";

  const KEY = /^[a-z0-9_]+(?:\.[a-z0-9_]+){0,7}$/;
  const PARAM = /^[a-zA-Z0-9_]{1,64}$/;
  const scopes = new Set();
  const listeners = new Set();

  function runtime() {
    return global.NuxivaScopedI18n || null;
  }

  function cleanParams(params) {
    const out = {};
    Object.entries(params || {}).forEach(([name, value]) => {
      if (PARAM.test(name) && ["string", "number", "boolean"].includes(typeof value)) out[name] = String(value);
    });
    return out;
  }

  function t(scope, key, params) {
    scopes.add(scope);
    const rt = runtime();
    if (!rt) {
      if (global.NUXIVA_I18N_BUNDLE && global.NUXIVA_I18N_BUNDLE.meta && global.NUXIVA_I18N_BUNDLE.meta.scope === scope) {
        const dict = global.NUXIVA_I18N_BUNDLE.dictionary || {};
        const val = dict[key];
        if (val != null) {
          return String(val).replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (_, k) => params && params[k] != null ? String(params[k]) : "");
        }
      }
      return "";
    }
    try {
      return rt.t(scope, key, cleanParams(params));
    } catch (error) {
      console.error("i18n: testo non risolto", scope, key, error);
      return "";
    }
  }

  function bind(el, key, params) {
    if (!el) return el;
    if (!KEY.test(key)) throw new TypeError(`chiave i18n non valida: ${key}`);
    const clean = cleanParams(params);
    if (Object.keys(clean).length) el.setAttribute("data-i18n-params", JSON.stringify(clean));
    else el.removeAttribute("data-i18n-params");
    el.setAttribute("data-i18n", key);
    return el;
  }

  function plain(el, text) {
    if (!el) return el;
    el.removeAttribute("data-i18n");
    el.removeAttribute("data-i18n-params");
    el.textContent = text == null ? "" : String(text);
    return el;
  }

  function escape(text) {
    return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function html(key, params, tag = "span") {
    if (!KEY.test(key)) throw new TypeError(`chiave i18n non valida: ${key}`);
    if (!["span", "b", "small", "strong", "em"].includes(tag)) throw new TypeError(`tag non ammesso: ${tag}`);
    const clean = cleanParams(params);
    const encoded = Object.keys(clean).length ? ` data-i18n-params="${escape(JSON.stringify(clean))}"` : "";
    return `<${tag} data-i18n="${key}"${encoded}></${tag}>`;
  }

  function attr(el, spec, params) {
    if (!el) return el;
    const clean = cleanParams(params);
    if (Object.keys(clean).length) el.setAttribute("data-i18n-params", JSON.stringify(clean));
    el.setAttribute("data-i18n-attr", Object.entries(spec).map(([name, key]) => `${name}:${key}`).join(","));
    return el;
  }

  function whenRuntime() {
    return new Promise((resolve) => {
      const check = () => (runtime() ? resolve(runtime()) : setTimeout(check, 25));
      check();
    });
  }

  async function ready(list) {
    list.forEach((s) => scopes.add(s));
    const rt = await whenRuntime();
    await Promise.all(list.map((s) => rt.preload(s)));
  }

  global.addEventListener("nuxiva:i18n:changed", async () => {
    const rt = runtime();
    if (rt) await Promise.all([...scopes].map((s) => rt.preload(s)));
    listeners.forEach((fn) => {
      try {
        fn();
      } catch (error) {
        console.error("i18n: aggiornamento testo non riuscito", error);
      }
    });
  });

  global.PageText = Object.freeze({
    t,
    bind,
    plain,
    attr,
    html,
    ready,
    scope: (name) => (key, params) => t(name, key, params),
    onChange: (fn) => listeners.add(fn),
  });
})(window);
