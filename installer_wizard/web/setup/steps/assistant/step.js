(() => {
  "use strict";

  class StepAssistant {
    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = window.SetupStepAssistantI18n.dict[lang] || window.SetupStepAssistantI18n.dict.it;
      return dict[key] || key;
    }

    render() {
      const gender = window.SetupStorage.get("assistantGender") || "female";
      const name = window.SetupStorage.get("assistantName") || "Nuxiva";

      const nameInp = document.getElementById("cfg-assist-name");
      if (nameInp && !nameInp.value) {
        nameInp.value = name;
      }

      const vFemale = document.getElementById("voice-female");
      const vMale = document.getElementById("voice-male");

      if (vFemale && vMale) {
        if (gender === "female") {
          vFemale.classList.add("os-card-selected");
          vMale.classList.remove("os-card-selected");
        } else {
          vMale.classList.add("os-card-selected");
          vFemale.classList.remove("os-card-selected");
        }
      }
    }

    applyTranslations() {
      const nameLbl = document.querySelector('[data-i18n="setup.assistant.name"]');
      const voiceLbl = document.querySelector('[data-i18n="setup.assistant.voice"]');
      const femLbl = document.querySelector('[data-i18n="setup.voice.female"]');
      const maleLbl = document.querySelector('[data-i18n="setup.voice.male"]');

      if (nameLbl) nameLbl.textContent = this.t("name_label");
      if (voiceLbl) voiceLbl.textContent = this.t("voice_label");
      if (femLbl) femLbl.textContent = this.t("voice_female");
      if (maleLbl) maleLbl.textContent = this.t("voice_male");
    }

    init() {
      const nameInp = document.getElementById("cfg-assist-name");
      if (nameInp) {
        nameInp.addEventListener("input", (e) => {
          window.SetupStorage.set("assistantName", e.target.value.trim() || "Nuxiva");
        });
      }

      const vFemale = document.getElementById("voice-female");
      const vMale = document.getElementById("voice-male");

      if (vFemale && vMale) {
        vFemale.addEventListener("click", () => {
          window.SetupStorage.set("assistantGender", "female");
          this.render();
        });
        vMale.addEventListener("click", () => {
          window.SetupStorage.set("assistantGender", "male");
          this.render();
        });
      }

      this.applyTranslations();
      this.render();
    }
  }

  window.SetupStepAssistant = new StepAssistant();
})();
