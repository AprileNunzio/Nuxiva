(() => {
  "use strict";

  const SUPPORTED = Object.freeze(["it", "en", "es", "fr"]);
  const SCOPE = "web/setup";
  const KEY = /^[a-z0-9][a-z0-9_-]{0,80}$/;
  const dictionaries = new Map();
  let activeLang = "it";

  function sanitize(payload, lang) {
    if (!payload || typeof payload !== "object" || !payload.meta || payload.meta.scope !== SCOPE || payload.meta.locale !== lang) {
      throw new Error(`setup i18n: bundle ${lang} non valido`);
    }
    const out = new Map();
    for (const [key, value] of Object.entries(payload.dictionary || {})) {
      if (KEY.test(key) && typeof value === "string") out.set(key, value);
    }
    return out;
  }

  async function load(lang) {
    if (dictionaries.has(lang)) return dictionaries.get(lang);
    const response = await fetch(`/static/setup/language/${lang}.json`, { credentials: "same-origin", cache: "no-cache", headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`setup i18n: ${lang} HTTP ${response.status}`);
    const dict = sanitize(await response.json(), lang);
    dictionaries.set(lang, dict);
    return dict;
  }

  function t(key, vars = {}) {
    const text = (dictionaries.get(activeLang) && dictionaries.get(activeLang).get(key)) ?? (dictionaries.get("it") && dictionaries.get("it").get(key)) ?? key;
    return Object.entries(vars).reduce((acc, [name, value]) => acc.replaceAll(`{${name}}`, String(value)), text);
  }

  function paint(root = document) {
    root.querySelectorAll("[data-st]").forEach((el) => {
      const key = el.getAttribute("data-st");
      if (el.tagName === "TITLE") document.title = t(key);
      else el.textContent = t(key);
    });
    root.querySelectorAll("[data-st-ph]").forEach((el) => el.setAttribute("placeholder", t(el.getAttribute("data-st-ph"))));
    root.querySelectorAll("[data-st-aria]").forEach((el) => el.setAttribute("aria-label", t(el.getAttribute("data-st-aria"))));
  }

  async function applyLanguage(lang) {
    const target = SUPPORTED.includes(lang) ? lang : "it";
    await load("it");
    if (target !== "it") await load(target);
    activeLang = target;
    document.documentElement.lang = activeLang;
    try {
      localStorage.setItem("nuxiva_ui_lang", activeLang);
    } catch (error) {
      console.warn("setup i18n: preferenza lingua non salvata", error);
    }
    paint();
    window.dispatchEvent(new CustomEvent("setup-i18n-changed", { detail: { lang: activeLang } }));
    return activeLang;
  }

  window.SetupI18n = Object.freeze({
    t,
    paint,
    applyLanguage,
    get current() { return activeLang; },
    supported: SUPPORTED
  });
})();
