(() => {
  "use strict";

  let activeLang = "it";

  function getDict(lang) {
    const dicts = window.SetupDict || {};
    return dicts[lang] || dicts.it || {};
  }

  function t(key, vars = {}) {
    const dict = getDict(activeLang);
    const fallback = getDict("it");
    let text = dict[key] !== undefined ? dict[key] : fallback[key] !== undefined ? fallback[key] : key;
    for (const [k, v] of Object.entries(vars)) {
      text = text.replaceAll(`{${k}}`, v);
    }
    return text;
  }

  function applyLanguage(lang) {
    const dicts = window.SetupDict || {};
    activeLang = dicts[lang] ? lang : "it";
    document.documentElement.lang = activeLang;

    try {
      localStorage.setItem("nuxiva_ui_lang", activeLang);
    } catch (_) {}

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (key) {
        if (el.tagName === "TITLE") {
          document.title = t(key);
        } else {
          el.textContent = t(key);
        }
      }
    });

    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      const key = el.getAttribute("data-i18n-ph");
      if (key) {
        el.setAttribute("placeholder", t(key));
      }
    });

    if (window.NuxivaI18n && typeof window.NuxivaI18n.setLanguage === "function") {
      window.NuxivaI18n.setLanguage(activeLang).catch(() => {});
    }

    window.dispatchEvent(new CustomEvent("setup-i18n-changed", { detail: { lang: activeLang } }));
  }

  window.SetupI18n = {
    t,
    applyLanguage,
    get current() { return activeLang; },
    get supported() { return ["it", "en", "es", "fr"]; }
  };
})();
