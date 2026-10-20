(() => {
  "use strict";

  const STORAGE_KEY = "nuxiva_reasoning_mode";

  class ReasoningModeSelector {
    constructor() {
      this.engines = [];
      this.currentMode = this.loadLocalMode();
      this.isOpen = false;
      this.rootElement = null;
      this.triggerBtn = null;
      this.menuEl = null;
      this.itemsContainer = null;
      this.iconEl = null;
      this.nameEl = null;
      this.verEl = null;
      this.countEl = null;
      this.init();
    }

    loadLocalMode() {
      try {
        return localStorage.getItem(STORAGE_KEY) || "";
      } catch (err) {
        return "";
      }
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
        if (!response.ok) return;

        const data = await response.json();
        const rawEngines = Array.isArray(data.modes)
          ? data.modes
          : Array.isArray(data.engines)
          ? data.engines
          : [];

        this.engines = rawEngines.map((m) => {
          const rawId = String(m.id || m.raw_version || m.version || "").trim();
          const cleanBadge = String(m.badge || m.version || rawId).replace(/^nuxiva-/i, "");
          const st = m.strategy || {};

          return {
            id: rawId,
            name: m.name || rawId,
            shortName: cleanBadge || m.name || rawId,
            version: cleanBadge,
            badge: cleanBadge,
            icon: m.icon || "🧠",
            pick: st.pick || "",
            pickParams: { n: st.candidates || 1, wait: st.wait_s || 0 },
            hint: m.hint || m.architecture || "",
            isDefault: !!m.is_default,
          };
        });

        const serverActive = data.mode ? String(data.mode).trim() : "";
        const defaultMode = data.default ? String(data.default).trim() : (this.engines[0] ? this.engines[0].id : "");

        if (!this.currentMode || !this.findEngine(this.currentMode)) {
          this.currentMode = serverActive || defaultMode;
        } else if (serverActive && this.findEngine(serverActive)) {
          this.currentMode = serverActive;
        }

        this.renderMenuItems();
        this.updateUi();

        if (window.NuxivaDisplay) {
          window.NuxivaDisplay.reasoningMode = this.currentMode;
        }
      } catch (err) {
        console.warn("Motori di ragionamento non letti", err);
      }
    }

    findEngine(query) {
      if (!query || !this.engines.length) return null;
      const q = String(query).trim().toLowerCase();
      return (
        this.engines.find((e) => e.id.toLowerCase() === q) ||
        this.engines.find((e) => e.version.toLowerCase() === q) ||
        this.engines.find((e) => e.name.toLowerCase() === q) ||
        this.engines.find((e) => e.id.toLowerCase().includes(q)) ||
        null
      );
    }

    getActiveEngine() {
      return this.findEngine(this.currentMode) || this.engines[0] || null;
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
        console.warn("Motore di ragionamento non salvato", err);
      }
    }

    setMode(mode, syncToServer = true) {
      const match = this.findEngine(mode);
      const chosenId = match ? match.id : mode;

      this.currentMode = chosenId;
      this.saveLocalMode(chosenId);

      if (window.NuxivaDisplay) {
        window.NuxivaDisplay.reasoningMode = chosenId;
      }

      this.updateUi();

      window.dispatchEvent(
        new CustomEvent("nuxiva:reasoning_mode_changed", {
          detail: { mode: chosenId, engine: match },
        })
      );

      if (syncToServer) {
        this.syncServerMode(chosenId);
      }
    }

    getMode() {
      return this.currentMode;
    }

    toggleMenu(force) {
      const willOpen = typeof force === "boolean" ? force : !this.isOpen;
      this.isOpen = willOpen;
      if (this.menuEl) {
        this.menuEl.hidden = !willOpen;
      }
      if (this.triggerBtn) {
        this.triggerBtn.classList.toggle("is-open", willOpen);
        this.triggerBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      }
    }

    closeMenu() {
      if (this.isOpen) {
        this.toggleMenu(false);
      }
    }

    renderMenuItems() {
      if (!this.itemsContainer) return;
      this.itemsContainer.innerHTML = "";

      if (this.countEl) {
        PageText.bind(this.countEl, this.engines.length === 1 ? "model_count_one" : "model_count_many", { n: this.engines.length });
      }

      if (!this.engines.length) {
        const empty = document.createElement("div");
        empty.className = "opt-hint";
        empty.style.padding = "10px";
        PageText.bind(empty, "model_scanning");
        this.itemsContainer.appendChild(empty);
        return;
      }

      this.engines.forEach((eng) => {
        const isActive = this.currentMode && eng.id.toLowerCase() === this.currentMode.toLowerCase();
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `dock-model-option ${isActive ? "is-active" : ""}`;
        btn.setAttribute("role", "menuitem");
        btn.setAttribute("data-engine-id", eng.id);
        btn.title = `${eng.name} (${eng.version})${eng.hint ? `: ${eng.hint}` : ""}`;
        const esc = window.Nuxiva.fmt.esc;

        btn.innerHTML = `
          <span class="opt-icon-col">${esc(eng.icon)}</span>
          <span class="opt-info">
            <span class="opt-top-row">
              <span class="opt-name">${esc(eng.name)}</span>
              <span class="opt-badge">${esc(eng.version)}</span>
              <span class="opt-sla">${eng.pick ? PageText.html(`ms_${eng.pick}`, eng.pickParams) : ""}</span>
            </span>
            ${eng.hint ? `<span class="opt-hint">${esc(eng.hint)}</span>` : ""}
          </span>
          <span class="opt-check">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </span>
        `;

        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.setMode(eng.id, true);
          this.closeMenu();
        });

        const row = document.createElement("div");
        row.className = "dock-model-row";
        const info = document.createElement("button");
        info.type = "button";
        info.className = "dock-model-info";
        info.textContent = "i";
        PageText.attr(info, { title: "model_info", "aria-label": "model_info" }, { name: eng.name });
        info.addEventListener("click", (e) => {
          e.stopPropagation();
          this.closeMenu();
          if (window.NuxivaReasoningInfo) window.NuxivaReasoningInfo.open(eng.id);
        });
        row.append(btn, info);
        this.itemsContainer.appendChild(row);
      });
    }

    updateUi() {
      const eng = this.getActiveEngine();
      if (!eng) return;

      if (this.iconEl) this.iconEl.textContent = eng.icon;
      if (this.nameEl) this.nameEl.textContent = eng.shortName;
      if (this.verEl) this.verEl.textContent = eng.version;
      if (this.triggerBtn) {
        PageText.attr(this.triggerBtn, { title: "model_active", "aria-label": "model_active" }, { name: eng.name, version: eng.version });
      }

      if (this.itemsContainer) {
        const all = this.itemsContainer.querySelectorAll(".dock-model-option");
        all.forEach((el) => {
          const id = el.getAttribute("data-engine-id");
          const active = id && id.toLowerCase() === this.currentMode.toLowerCase();
          el.classList.toggle("is-active", !!active);
        });
      }
    }

    bindEvents() {
      if (this.triggerBtn) {
        this.triggerBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.toggleMenu();
        });
      }

      document.addEventListener("click", (e) => {
        if (!this.rootElement || !this.rootElement.contains(e.target)) {
          this.closeMenu();
        }
      });

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && this.isOpen) {
          this.closeMenu();
          if (this.triggerBtn) this.triggerBtn.focus();
        }
      });
    }

    mount() {
      this.rootElement = document.getElementById("reasoning-selector-root");
      this.triggerBtn = document.getElementById("btn-model-trigger");
      this.menuEl = document.getElementById("dock-model-menu");
      this.itemsContainer = document.getElementById("dock-model-items");
      this.iconEl = document.getElementById("dock-model-icon");
      this.nameEl = document.getElementById("dock-model-name");
      this.verEl = document.getElementById("dock-model-ver-text");
      this.countEl = document.getElementById("dock-model-count");

      if (this.triggerBtn && this.menuEl && this.itemsContainer) {
        this.bindEvents();
        this.renderMenuItems();
        this.updateUi();
      }
    }

    init() {
      const setup = () => {
        this.mount();
        this.fetchServerMode();
      };

      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
      } else {
        setup();
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
