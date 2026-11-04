import { bus } from "./bus.js";
import { i18n } from "./i18n.js";
import { ConfigureStepView } from "./configure-view.js";

export class StepFlowWidget {
  constructor() {
    this.elTitle = document.getElementById("window-title");
    this.elSubtitle = document.getElementById("window-subtitle");
    this.elBody = document.getElementById("window-body");
    this.elActions = document.getElementById("window-actions");
    this.currentStep = null;
    this.selectedLang = "it";
    this.autoAdvanceTimer = null;
    this.countdownSeconds = 25;
    this.updateCheckPassed = false;
    this.updateChecking = false;
    this.renderedMode = null;
    this.renderedStepId = null;
    this.configureView = new ConfigureStepView(() => { this.renderedMode = null; });
  }

  mount() {
    bus.on("journey:step", (step) => this.renderStep(step));
    bus.on("i18n:changed", () => {
      if (this.renderedMode === "lang") {
        this.renderLanguageSelection();
      } else if (this.currentStep && this.renderedMode !== "update") {
        this.renderedStepId = null;
        this.renderStep(this.currentStep);
      }
    });
  }

  renderStep(step) {
    this.currentStep = step;
    if (!this.elBody || !this.elActions) return;

    this.clearAutoAdvance();

    if (!step || step.stage === "pending" || step.stage === "new") {
      if (this.renderedMode !== "lang") {
        this.renderedMode = "lang";
        this.renderLanguageSelection();
      }
      return;
    }

    this.updateCheckPassed = true;
    const drawerBtn = document.getElementById("terminal-drawer-btn");
    if (drawerBtn) drawerBtn.style.display = "";

    if (step.status === "failed") {
      this.renderedMode = "failed";
      this.renderedStepId = step.id;
      this.renderFailure(step);
      return;
    }

    if (step.requires_decision && Array.isArray(step.choices) && step.choices.length > 0) {
      if (this.renderedMode !== "decision" || this.renderedStepId !== step.id) {
        this.renderedMode = "decision";
        this.renderedStepId = step.id;
        this.renderDecision(step);
      }
      return;
    }

    if (step.kind === "configure") {
      if (this.renderedMode !== "configure" || this.renderedStepId !== step.id) {
        this.renderedMode = "configure";
        this.renderedStepId = step.id;
        const titleKey = `step_${step.id}_title`;
        const descKey = `step_${step.id}_desc`;
        if (this.elTitle) this.elTitle.textContent = i18n.t(titleKey, step.id);
        if (this.elSubtitle) this.elSubtitle.textContent = i18n.t(descKey, "Configurazione richiesta per procedere.");
        this.configureView.render(this.elBody, this.elActions, step);
      }
      return;
    }

    if (this.renderedMode !== "running" || this.renderedStepId !== step.id) {
      this.renderedMode = "running";
      this.renderedStepId = step.id;
      this.renderRunning(step);
    }
  }

  clearAutoAdvance() {
    if (this.autoAdvanceTimer) {
      clearInterval(this.autoAdvanceTimer);
      this.autoAdvanceTimer = null;
    }
  }

  renderUpdateCheck() {
    const drawerBtn = document.getElementById("terminal-drawer-btn");
    if (drawerBtn) drawerBtn.style.display = "none";

    if (this.elTitle) this.elTitle.textContent = i18n.t("update_title", "Controllo disponibilità aggiornamenti online");
    if (this.elSubtitle) this.elSubtitle.textContent = i18n.t("update_desc", "Verifica della presenza di nuovi commit prima di procedere con la configurazione.");

    this.elBody.innerHTML = `
      <div class="update-check-card">
        <div class="update-badge-row">
          <span class="badge-label">${i18n.t("update_local_rev", "Revisione locale:")}</span>
          <span class="badge-val" id="update-local-rev">...</span>
        </div>
        <div class="update-status-anim">
          <div class="update-spinner" id="update-spinner"></div>
          <p class="update-status-txt" id="update-status-txt">${i18n.t("update_status_checking", "Controllo disponibilità aggiornamenti online in corso...")}</p>
        </div>
        <div class="update-changelog-wrap" id="update-changelog-wrap" style="display: none;">
          <div class="update-changelog-title">${i18n.t("update_changelog_title", "Novità dell'aggiornamento:")}</div>
          <div class="update-changelog-list" id="update-changelog-list"></div>
        </div>
      </div>
    `;

    this.elActions.innerHTML = `
      <button type="button" class="btn-os-primary" id="btn-update-next" style="display: none;">
        <span>${i18n.t("btn_update_next", "Avanti")} &rarr;</span>
      </button>
      <button type="button" class="btn-os-secondary" id="btn-update-retry" style="display: none;">
        <span>${i18n.t("btn_update_retry", "Riprova")}</span>
      </button>
    `;

    const btnNext = document.getElementById("btn-update-next");
    if (btnNext) {
      btnNext.addEventListener("click", () => {
        this.updateCheckPassed = true;
        this.renderedMode = "lang";
        this.renderLanguageSelection();
      });
    }

    const btnRetry = document.getElementById("btn-update-retry");
    if (btnRetry) {
      btnRetry.addEventListener("click", () => {
        this.runUpdateSync();
      });
    }

    this.runUpdateSync();
  }

  async runUpdateSync() {
    if (this.updateChecking) return;
    this.updateChecking = true;

    const elRev = document.getElementById("update-local-rev");
    const elTxt = document.getElementById("update-status-txt");
    const elSpin = document.getElementById("update-spinner");
    const elNext = document.getElementById("btn-update-next");
    const elRetry = document.getElementById("btn-update-retry");
    const elWrap = document.getElementById("update-changelog-wrap");
    const elList = document.getElementById("update-changelog-list");

    if (elNext) elNext.style.display = "none";
    if (elRetry) elRetry.style.display = "none";
    if (elSpin) {
      elSpin.className = "update-spinner";
      elSpin.innerHTML = "";
    }
    if (elTxt) elTxt.textContent = i18n.t("update_status_checking", "Controllo disponibilità aggiornamenti online in corso...");

    try {
      const getRes = await fetch(`/api/setup/update?t=${Date.now()}`);
      if (getRes.ok) {
        const getMeta = await getRes.json();
        if (elRev && (getMeta.local_short || getMeta.local_rev)) {
          elRev.textContent = getMeta.local_short || getMeta.local_rev.substring(0, 8);
        }
      }
    } catch (e) {
    }

    try {
      const res = await fetch("/api/setup/update/sync", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Nuxiva-Request": "1"
        }
      });
      const data = await res.json();
      this.updateChecking = false;

      if (!res.ok || data.success === false) {
        throw new Error(data.error || data.detail || i18n.t("update_status_error", "Errore durante la verifica online"));
      }

      if (elRev && (data.local_short || data.local_rev)) {
        const rev = data.local_short || data.local_rev;
        elRev.textContent = rev.substring(0, 8);
      }

      if (elSpin) {
        elSpin.className = "update-spinner success";
        elSpin.innerHTML = "&#10003;";
      }

      if (data.applied) {
        if (elTxt) elTxt.textContent = i18n.t("update_status_updated", "Aggiornamento completato con successo. Nuovi commit applicati.");
        if (Array.isArray(data.changelog) && data.changelog.length > 0 && elWrap && elList) {
          elList.innerHTML = data.changelog.map((c) => `<div>&bull; ${c}</div>`).join("");
          elWrap.style.display = "block";
        }
      } else {
        if (elTxt) elTxt.textContent = i18n.t("update_status_up_to_date", "Nessun nuovo aggiornamento disponibile. Il sistema è aggiornato.");
      }

      if (elNext) elNext.style.display = "inline-flex";
    } catch (err) {
      this.updateChecking = false;
      if (elTxt) elTxt.textContent = err.message || i18n.t("update_status_error", "Impossibile verificare gli aggiornamenti online.");
      if (elRetry) elRetry.style.display = "inline-flex";
      if (elNext) elNext.style.display = "inline-flex";
    }
  }

  renderLanguageSelection() {
    const drawerBtn = document.getElementById("terminal-drawer-btn");
    if (drawerBtn) drawerBtn.style.display = "none";

    if (this.elTitle) this.elTitle.textContent = i18n.t("choose_language", "Seleziona la lingua di sistema");
    if (this.elSubtitle) this.elSubtitle.textContent = i18n.t("choose_language_desc", "Configura la lingua predefinita dell'interfaccia e dei servizi vocali.");

    this.elBody.innerHTML = `
      <div class="lang-selection-grid">
        <button type="button" class="lang-tile ${this.selectedLang === "it" ? "selected" : ""}" data-lang="it">
          <span class="tile-code">IT</span>
          <span class="tile-name">Italiano</span>
        </button>
        <button type="button" class="lang-tile ${this.selectedLang === "en" ? "selected" : ""}" data-lang="en">
          <span class="tile-code">EN</span>
          <span class="tile-name">English</span>
        </button>
        <button type="button" class="lang-tile ${this.selectedLang === "es" ? "selected" : ""}" data-lang="es">
          <span class="tile-code">ES</span>
          <span class="tile-name">Español</span>
        </button>
        <button type="button" class="lang-tile ${this.selectedLang === "fr" ? "selected" : ""}" data-lang="fr">
          <span class="tile-code">FR</span>
          <span class="tile-name">Français</span>
        </button>
      </div>
    `;

    this.elBody.querySelectorAll(".lang-tile").forEach((tile) => {
      tile.addEventListener("click", () => {
        const lang = tile.getAttribute("data-lang");
        this.selectedLang = lang;
        i18n.setLanguage(lang);
      });
    });

    this.elActions.innerHTML = `
      <button type="button" class="btn-os-primary" id="btn-start-activation">
        <span>${i18n.t("btn_start_install", "Avvia installazione")}</span>
      </button>
    `;

    const btnStart = document.getElementById("btn-start-activation");
    if (btnStart) {
      btnStart.addEventListener("click", () => this.startActivation());
    }
  }

  async startActivation() {
    try {
      const btn = document.getElementById("btn-start-activation");
      if (btn) btn.disabled = true;

      await fetch("/api/activation/language", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: this.selectedLang })
      });
      await fetch("/api/activation/advance", { method: "POST" });
    } catch (e) {
      console.error(e);
    }
  }

  renderRunning(step) {
    if (this.elTitle) this.elTitle.textContent = "Nuxiva OS";
    const descKey = `step_${step.id}_desc`;
    const defaultDesc = `Installazione del modulo ${step.id || "sistema"} in corso sul disco principale.`;
    if (this.elSubtitle) this.elSubtitle.textContent = i18n.t(descKey, defaultDesc);

    this.elBody.innerHTML = `
      <div class="install-hero">
        <div class="install-component-icon">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
            <line x1="6" y1="6" x2="6.01" y2="6"/>
            <line x1="6" y1="18" x2="6.01" y2="18"/>
          </svg>
        </div>

        <div class="os-progress-container">
          <div class="os-progress-track">
            <div class="os-progress-fill" id="os-progress-fill"></div>
          </div>
          <div class="os-progress-info">
            <span id="os-progress-time">Circa 2 minuti rimanenti</span>
            <span id="os-progress-pct">0%</span>
          </div>

          <div class="os-download-strip" id="os-download-strip">
            <div class="download-track">
              <div class="download-fill" id="download-fill"></div>
            </div>
            <div class="download-labels">
              <span id="download-stats-lbl">0.0 / 0.0 MB</span>
              <span id="download-speed-lbl">0.0 KB/s</span>
            </div>
          </div>
        </div>
      </div>
    `;

    this.elActions.innerHTML = "";
  }

  renderDecision(step) {
    const titleKey = `step_${step.id}_title`;
    const descKey = `step_${step.id}_desc`;
    const title = i18n.t(titleKey, i18n.t("decision_required_title", "Decisione richiesta"));
    const desc = i18n.t(descKey, "Seleziona una delle opzioni disponibili per procedere con l'installazione.");

    if (this.elTitle) this.elTitle.textContent = title;
    if (this.elSubtitle) this.elSubtitle.textContent = desc;

    const cardsHtml = step.choices.map((choice) => {
      const cTitleKey = `choice_${choice.id}_title`;
      const cDescKey = `choice_${choice.id}_desc`;
      const cTitle = i18n.t(cTitleKey, choice.id.toUpperCase());
      const cDesc = i18n.t(cDescKey, choice.installs ? "Installa e attiva componente sul dispositivo" : "Posticipa o disattiva componente");
      const badge = choice.recommended ? `<span class="recommended-pill">${i18n.t("recommended_badge", "CONSIGLIATO")}</span>` : "";

      return `
        <div class="decision-card" data-choice-id="${choice.id}">
          <div class="decision-card-header">
            <span class="decision-card-title">${cTitle}</span>
            ${badge}
          </div>
          <p class="decision-card-desc">${cDesc}</p>
        </div>
      `;
    }).join("");

    this.elBody.innerHTML = `
      <div class="decision-deck">${cardsHtml}</div>
    `;

    this.countdownSeconds = 25;
    this.elActions.innerHTML = `
      <div style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); display: flex; align-items: center; gap: 8px;">
        <span id="auto-advance-countdown">Avanzamento automatico tra ${this.countdownSeconds}s...</span>
        <button type="button" class="btn-os-secondary" id="btn-skip-choice" style="padding: 4px 12px; font-size: 0.75rem;">Salta</button>
      </div>
    `;

    const fallbackChoice = step.choices.find((c) => !c.installs) || step.choices[0];

    const applyChoiceAndAdvance = async (choiceId) => {
      this.clearAutoAdvance();
      this.elBody.querySelectorAll(".decision-card").forEach((c) => {
        c.style.opacity = "0.5";
        c.style.pointerEvents = "none";
      });
      try {
        await fetch(`/api/activation/choice/${step.id}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ choice: choiceId })
        });
        await fetch("/api/activation/advance", { method: "POST" });
      } catch (e) {
        console.error(e);
      }
    };

    this.elBody.querySelectorAll(".decision-card").forEach((card) => {
      card.addEventListener("click", () => {
        const choiceId = card.getAttribute("data-choice-id");
        applyChoiceAndAdvance(choiceId);
      });
    });

    const btnSkip = document.getElementById("btn-skip-choice");
    if (btnSkip) {
      btnSkip.addEventListener("click", () => {
        applyChoiceAndAdvance(fallbackChoice ? fallbackChoice.id : "later");
      });
    }

    const countdownEl = document.getElementById("auto-advance-countdown");
    this.autoAdvanceTimer = setInterval(() => {
      this.countdownSeconds -= 1;
      if (countdownEl) {
        countdownEl.textContent = `Avanzamento automatico tra ${this.countdownSeconds}s...`;
      }
      if (this.countdownSeconds <= 0) {
        this.clearAutoAdvance();
        applyChoiceAndAdvance(fallbackChoice ? fallbackChoice.id : "later");
      }
    }, 1000);
  }

  renderFailure(step) {
    if (this.elTitle) this.elTitle.textContent = i18n.t("step_failed_title", "Operazione non completata");
    if (this.elSubtitle) this.elSubtitle.textContent = step.error_message || i18n.t("step_failed_desc", "Si è verificato un errore durante la sequenza.");

    this.elBody.innerHTML = `
      <div style="padding: 16px; color: var(--amber-warning); font-size: 0.9rem; max-width: 500px;">
        ${step.error_message || i18n.t("step_retry_prompt", "È possibile riprovare la sequenza o procedere saltandola.")}
      </div>
    `;

    this.elActions.innerHTML = `
      <button type="button" class="btn-os-primary" id="btn-retry-step">
        <span>${i18n.t("btn_retry", "Riprova")}</span>
      </button>
      <button type="button" class="btn-os-secondary" id="btn-skip-step">
        <span>${i18n.t("btn_skip", "Salta")}</span>
      </button>
    `;

    const btnRetry = document.getElementById("btn-retry-step");
    if (btnRetry) {
      btnRetry.addEventListener("click", async () => {
        btnRetry.disabled = true;
        await fetch(`/api/activation/retry/${step.id}`, { method: "POST" });
        await fetch("/api/activation/advance", { method: "POST" });
      });
    }

    const btnSkip = document.getElementById("btn-skip-step");
    if (btnSkip) {
      btnSkip.addEventListener("click", async () => {
        btnSkip.disabled = true;
        await fetch(`/api/activation/skip/${step.id}`, { method: "POST" });
        await fetch("/api/activation/advance", { method: "POST" });
      });
    }
  }
}
