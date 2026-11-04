import { bus } from "./bus.js";

export class I18nManager {
  constructor() {
    this.currentLang = "it";
    this.dict = {};
    this.supported = ["it", "en", "es", "fr"];
  }

  async setLanguage(lang) {
    if (!this.supported.includes(lang)) {
      lang = "it";
    }
    this.currentLang = lang;
    try {
      const res = await fetch(`/static/activation/language/${lang}.json?t=${Date.now()}`);
      if (res.ok) {
        const raw = await res.json();
        this.dict = raw.dictionary || raw;
        this.applyTranslations();
        bus.emit("i18n:changed", { lang: this.currentLang, dict: this.dict });
      }
    } catch (e) {
      console.error(e);
    }
  }

  t(key, fallback = "") {
    return this.dict[key] || fallback || key;
  }

  applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (this.dict[key]) {
        el.textContent = this.dict[key];
      }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (this.dict[key]) {
        el.setAttribute("placeholder", this.dict[key]);
      }
    });
  }
}

export const i18n = new I18nManager();
