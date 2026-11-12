import { i18n } from "./i18n.js";

export class ConfigureStepView {
  constructor(onAdvance) {
    this.onAdvance = onAdvance;
    this.selectedVoice = "female";
  }

  render(bodyEl, actionsEl, step) {
    let formHtml = "";
    if (step.id === "assistant_naming") {
      formHtml = `
        <div class="configure-form-group">
          <label class="configure-label" for="cfg-assistant-name">${i18n.t("cfg_name_label", "Nome Assistente")}</label>
          <input type="text" id="cfg-assistant-name" class="configure-input" value="NUXIVA" maxlength="32" autofocus />
        </div>
      `;
    } else if (step.id === "assistant_voice") {
      formHtml = `
        <div class="configure-form-group">
          <label class="configure-label">${i18n.t("cfg_voice_label", "Voce Assistente")}</label>
          <div class="decision-deck" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
            <div class="decision-card selected" data-voice="female" id="voice-opt-female">
              <span class="decision-card-title">${i18n.t("voice_female", "Voce Femminile")}</span>
            </div>
            <div class="decision-card" data-voice="male" id="voice-opt-male">
              <span class="decision-card-title">${i18n.t("voice_male", "Voce Maschile")}</span>
            </div>
          </div>
        </div>
      `;
    } else if (step.id === "owner_identity") {
      formHtml = `
        <div class="configure-form-group">
          <label class="configure-label" for="cfg-owner-first">${i18n.t("cfg_first_name", "Nome Proprietario")}</label>
          <input type="text" id="cfg-owner-first" class="configure-input" maxlength="48" required />
          <label class="configure-label" for="cfg-owner-last" style="margin-top: 10px;">${i18n.t("cfg_last_name", "Cognome (opzionale)")}</label>
          <input type="text" id="cfg-owner-last" class="configure-input" maxlength="48" />
        </div>
      `;
    } else {
      formHtml = `
        <div class="configure-form-group">
          <p class="configure-generic-info">${i18n.t("cfg_generic_desc", "Conferma per applicare la configurazione predefinita.")}</p>
        </div>
      `;
    }

    bodyEl.innerHTML = `<div class="configure-deck">${formHtml}</div>`;

    actionsEl.innerHTML = `
      <button type="button" class="btn-os-secondary" id="btn-cfg-defer" style="display: ${step.skippable ? "inline-flex" : "none"}">
        ${i18n.t("btn_skip", "Salta")}
      </button>
      <button type="button" class="btn-os-primary" id="btn-cfg-submit">
        <span>${i18n.t("btn_confirm", "Conferma e Continua")} &rarr;</span>
      </button>
    `;

    this.bindEvents(bodyEl, step);
  }

  bindEvents(bodyEl, step) {
    const femaleCard = bodyEl.querySelector("#voice-opt-female");
    const maleCard = bodyEl.querySelector("#voice-opt-male");
    if (femaleCard && maleCard) {
      femaleCard.addEventListener("click", () => {
        femaleCard.classList.add("selected");
        maleCard.classList.remove("selected");
        this.selectedVoice = "female";
      });
      maleCard.addEventListener("click", () => {
        maleCard.classList.add("selected");
        femaleCard.classList.remove("selected");
        this.selectedVoice = "male";
      });
    }

    const btnSubmit = document.getElementById("btn-cfg-submit");
    if (btnSubmit) {
      btnSubmit.addEventListener("click", () => this.submitPayload(step));
    }

    const btnDefer = document.getElementById("btn-cfg-defer");
    if (btnDefer) {
      btnDefer.addEventListener("click", () => this.deferStep(step));
    }
  }

  collectPayload(step) {
    if (step.id === "assistant_naming") {
      const input = document.getElementById("cfg-assistant-name");
      return { name: input ? input.value.trim() : "NUXIVA" };
    }
    if (step.id === "assistant_voice") {
      return { gender: this.selectedVoice };
    }
    if (step.id === "owner_identity") {
      const first = document.getElementById("cfg-owner-first");
      const last = document.getElementById("cfg-owner-last");
      return {
        first_name: first ? first.value.trim() : "Proprietario",
        last_name: last ? last.value.trim() : ""
      };
    }
    return { enabled: true };
  }

  async submitPayload(step) {
    const payload = this.collectPayload(step);
    const btn = document.getElementById("btn-cfg-submit");
    if (btn) btn.disabled = true;

    try {
      const res = await fetch(`/api/activation/configure/${step.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        await fetch("/api/activation/advance", { method: "POST" });
        if (this.onAdvance) this.onAdvance();
      }
    } catch (e) {
      console.error(e);
      if (btn) btn.disabled = false;
    }
  }

  async deferStep(step) {
    const btn = document.getElementById("btn-cfg-defer");
    if (btn) btn.disabled = true;

    try {
      const res = await fetch(`/api/activation/defer/${step.id}`, { method: "POST" });
      if (res.ok) {
        await fetch("/api/activation/advance", { method: "POST" });
        if (this.onAdvance) this.onAdvance();
      }
    } catch (e) {
      console.error(e);
      if (btn) btn.disabled = false;
    }
  }
}
