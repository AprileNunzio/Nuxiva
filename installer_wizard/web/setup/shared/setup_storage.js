(() => {
  "use strict";

  const STORAGE_KEY = "nuxiva_setup_permanent_state";
  const COOKIE_PREFIX = "nuxiva_setup_";

  const defaultState = {
    step: 0,
    theme: "dark",
    lang: "it",
    mode: "standard",
    storage: "clean",
    selectedComponents: ["voice", "ear", "vision", "sandbox", "brain_local"],
    assistantName: "Nuxiva",
    assistantGender: "female",
    ownerFirst: "",
    ownerLast: ""
  };

  function setCookie(name, value, days = 365) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${COOKIE_PREFIX}${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
  }

  function getCookie(name) {
    const key = `${COOKIE_PREFIX}${name}=`;
    const parts = document.cookie.split(";");
    for (let part of parts) {
      let c = part.trim();
      if (c.indexOf(key) === 0) {
        return decodeURIComponent(c.substring(key.length));
      }
    }
    return null;
  }

  class SetupStorage {
    constructor() {
      this.state = this.load();
    }

    load() {
      let loaded = {};
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          loaded = JSON.parse(raw);
        }
      } catch (e) {
      }

      const merged = { ...defaultState, ...loaded };

      const cookieLang = getCookie("lang");
      if (cookieLang) merged.lang = cookieLang;

      const cookieTheme = getCookie("theme");
      if (cookieTheme) merged.theme = cookieTheme;

      const cookieStep = getCookie("step");
      if (cookieStep !== null && !isNaN(parseInt(cookieStep, 10))) {
        merged.step = parseInt(cookieStep, 10);
      }

      return merged;
    }

    save() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
      } catch (e) {
      }

      setCookie("lang", this.state.lang);
      setCookie("theme", this.state.theme);
      setCookie("step", this.state.step);
      setCookie("mode", this.state.mode);
      setCookie("storage", this.state.storage);
    }

    get(key) {
      return this.state[key];
    }

    set(key, value) {
      this.state[key] = value;
      this.save();
    }

    update(partial) {
      Object.assign(this.state, partial);
      this.save();
    }

    clear() {
      this.state = { ...defaultState };
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (e) {
      }
      setCookie("step", 0, -1);
    }
  }

  window.SetupStorage = new SetupStorage();
})();
