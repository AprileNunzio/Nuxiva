(() => {
  "use strict";

  const STORAGE_KEY = "nuxiva_reasoning_mode";
  const DEFAULT_MODE = "reasoning";

  const I18N = {
    it: {
      mode_fast_name: "Nuxiva 5.0 Veloce",
      mode_fast_badge: "5.0-flash",
      mode_fast_title: "Modalità Veloce (<180ms): risposte istantanee",
      mode_reasoning_name: "Nuxiva 5.0 Pro",
      mode_reasoning_badge: "5.0-pro",
      mode_reasoning_title: "Modalità Ragionamento: pensiero profondo e parallelo",
    },
    en: {
      mode_fast_name: "Nuxiva 5.0 Fast",
      mode_fast_badge: "5.0-flash",
      mode_fast_title: "Fast Mode (<180ms): instant responses",
      mode_reasoning_name: "Nuxiva 5.0 Pro",
      mode_reasoning_badge: "5.0-pro",
      mode_reasoning_title: "Reasoning Mode: deep parallel cortical thinking",
    },
    fr: {
      mode_fast_name: "Nuxiva 5.0 Rapide",
      mode_fast_badge: "5.0-flash",
      mode_fast_title: "Mode Rapide (<180ms): réponses instantanées",
      mode_reasoning_name: "Nuxiva 5.0 Pro",
      mode_reasoning_badge: "5.0-pro",
      mode_reasoning_title: "Mode Raisonnement: pensée profonde corticale",
    },
    de: {
      mode_fast_name: "Nuxiva 5.0 Schnell",
      mode_fast_badge: "5.0-flash",
      mode_fast_title: "Schneller Modus (<180ms): sofortige Antworten",
      mode_reasoning_name: "Nuxiva 5.0 Pro",
      mode_reasoning_badge: "5.0-pro",
      mode_reasoning_title: "Denkmodus: tiefe parallele kortikale Logik",
    },
    es: {
      mode_fast_name: "Nuxiva 5.0 Rápido",
      mode_fast_badge: "5.0-flash",
      mode_fast_title: "Modo Rápido (<180ms): respuestas instantáneas",
      mode_reasoning_name: "Nuxiva 5.0 Pro",
      mode_reasoning_badge: "5.0-pro",
      mode_reasoning_title: "Modo Razonamiento: pensamiento cortical profundo",
    },
  };

  function getLang() {
    const raw = (document.documentElement.lang || navigator.language || "it").slice(0, 2).toLowerCase();
    return I18N[raw] ? raw : "it";
  }

  function t(key) {
    const dict = I18N[getLang()] || I18N.it;
    return dict[key] || I18N.it[key] || key;
  }

  class ReasoningModeSelector {
    constructor() {
      this.currentMode = this.loadLocalMode();
      this.rootElement = null;
      this.btnFast = null;
      this.btnReasoning = null;
      this.init();
    }

    loadLocalMode() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === "fast" || stored === "reasoning") {
          return stored;
        }
      } catch (err) {
        return DEFAULT_MODE;
      }
      return DEFAULT_MODE;
    }

    saveLocalMode(mode) {
      try {
        localStorage.setItem(STORAGE_KEY, mode);
      } catch (err) {
        return;
      }
    }

    async fetchServerMode() {
      try {
        const response = await fetch("/api/assistant/mode", { method: "GET" });
        if (response.ok) {
          const data = await response.json();
          if (data && (data.mode === "fast" || data.mode === "reasoning")) {
            this.setMode(data.mode, false);
          }
        }
      } catch (err) {
        return;
      }
    }

    async syncServerMode(mode) {
      try {
        const speaker = window.NuxivaDisplay && window.NuxivaDisplay.currentSpeaker ? window.NuxivaDisplay.currentSpeaker : "";
        await fetch("/api/assistant/mode", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode, speaker }),
        });
      } catch (err) {
        return;
      }
    }

    setMode(mode, syncToServer = true) {
      const sanitized = mode === "fast" ? "fast" : "reasoning";
      this.currentMode = sanitized;
      this.saveLocalMode(sanitized);

      if (window.NuxivaDisplay) {
        window.NuxivaDisplay.reasoningMode = sanitized;
      }

      this.updateUi();

      window.dispatchEvent(
        new CustomEvent("nuxiva:reasoning_mode_changed", {
          detail: { mode: sanitized },
        })
      );

      if (syncToServer) {
        this.syncServerMode(sanitized);
      }
    }

    getMode() {
      return this.currentMode;
    }

    updateUi() {
      if (!this.btnFast || !this.btnReasoning) return;

      const isFast = this.currentMode === "fast";
      this.btnFast.classList.toggle("active", isFast);
      this.btnFast.setAttribute("aria-pressed", isFast ? "true" : "false");

      this.btnReasoning.classList.toggle("active", !isFast);
      this.btnReasoning.setAttribute("aria-pressed", !isFast ? "true" : "false");

      const fastNameEl = document.getElementById("mode-fast-name-text");
      const fastVerEl = document.getElementById("mode-fast-ver-text");
      const rNameEl = document.getElementById("mode-reasoning-name-text");
      const rVerEl = document.getElementById("mode-reasoning-ver-text");

      if (fastNameEl) fastNameEl.textContent = t("mode_fast_name");
      if (fastVerEl) fastVerEl.textContent = t("mode_fast_badge");
      if (rNameEl) rNameEl.textContent = t("mode_reasoning_name");
      if (rVerEl) rVerEl.textContent = t("mode_reasoning_badge");

      this.btnFast.title = t("mode_fast_title");
      this.btnReasoning.title = t("mode_reasoning_title");
    }

    bindEvents() {
      if (this.btnFast) {
        this.btnFast.addEventListener("click", () => this.setMode("fast", true));
      }
      if (this.btnReasoning) {
        this.btnReasoning.addEventListener("click", () => this.setMode("reasoning", true));
      }
      window.addEventListener("languagechange", () => this.updateUi());
      window.addEventListener("nuxiva:language_changed", () => this.updateUi());
    }

    mount() {
      this.btnFast = document.getElementById("btn-mode-fast");
      this.btnReasoning = document.getElementById("btn-mode-reasoning");
      this.rootElement = document.getElementById("reasoning-selector-root");

      if (this.btnFast && this.btnReasoning) {
        this.bindEvents();
        this.updateUi();
      }
    }

    init() {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
          this.mount();
          this.fetchServerMode();
        });
      } else {
        this.mount();
        this.fetchServerMode();
      }

      if (window.NuxivaDisplay) {
        window.NuxivaDisplay.reasoningMode = this.currentMode;
        window.NuxivaDisplay.getReasoningMode = () => this.getMode();
        window.NuxivaDisplay.setReasoningMode = (m) => this.setMode(m, true);
      }
    }
  }

  const instance = new ReasoningModeSelector();
  window.NuxivaReasoningSelector = instance;
})();
