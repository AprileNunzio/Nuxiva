(function (global) {
  "use strict";

  const LANGS = Object.freeze(["it", "en", "fr", "es"]);
  const RTL = Object.freeze(["ar", "he", "fa", "ur"]);
  const allowed = (lang) => LANGS.includes(String(lang || ""));

  function stored() {
    try {
      return localStorage.getItem("nuxiva_ui_lang") || "";
    } catch (error) {
      console.warn("i18n: preferenza lingua non leggibile", error);
      return "";
    }
  }

  function pick() {
    const candidates = [global.NUXIVA_UI_LANG, stored(), document.documentElement.lang, navigator.language];
    const found = candidates.map((c) => String(c || "").slice(0, 2).toLowerCase()).find(allowed);
    return found || "it";
  }

  let current = pick();

  function apply(lang) {
    current = lang;
    document.documentElement.lang = lang;
    document.documentElement.dir = RTL.includes(lang) ? "rtl" : "ltr";
    document.dispatchEvent(new CustomEvent("nuxiva-translated", { detail: lang }));
  }

  async function remember(lang) {
    try {
      localStorage.setItem("nuxiva_ui_lang", lang);
    } catch (error) {
      console.warn("i18n: preferenza lingua non salvata", error);
    }
    global.NUXIVA_UI_LANG = lang;
    const response = await fetch("/api/locale/ui", {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
      body: JSON.stringify({ lang }),
    });
    if (!response.ok) console.warn("i18n: lingua non salvata sul server", response.status);
  }

  async function switchTo(lang, persist = true) {
    if (!allowed(lang) || lang === current) return;
    if (persist) {
      try {
        await remember(lang);
      } catch (error) {
        console.warn("i18n: lingua non salvata", error);
      }
    }
    apply(lang);
  }

  document.documentElement.lang = current;
  global.NuxivaI18n = Object.freeze({
    setLanguage: (lang) => switchTo(lang, true),
    switchTo,
    language: () => current,
    languages: LANGS,
  });
})(window);
