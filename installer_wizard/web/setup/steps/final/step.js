(() => {
  "use strict";

  class StepFinal {
    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = window.SetupStepFinalI18n.dict[lang] || window.SetupStepFinalI18n.dict.it;
      return dict[key] || key;
    }

    render() {
      const storage = window.SetupStorage;
      const langCode = storage.get("lang") || "it";
      const mode = storage.get("mode") || "standard";
      const storageOpt = storage.get("storage") || "clean";
      const components = storage.get("selectedComponents") || [];
      const assistName = storage.get("assistantName") || "Nuxiva";
      const assistGender = storage.get("assistantGender") || "female";
      const first = storage.get("ownerFirst") || "Proprietario";
      const last = storage.get("ownerLast") || "";

      const sumLang = document.getElementById("sum-lang");
      const sumMode = document.getElementById("sum-mode");
      const sumStorage = document.getElementById("sum-storage");
      const sumComponents = document.getElementById("sum-components");
      const sumAssist = document.getElementById("sum-assistant");
      const sumOwner = document.getElementById("sum-owner");

      const langObj = (window.SetupStepLangI18n && window.SetupStepLangI18n.languages)
        ? window.SetupStepLangI18n.languages.find((l) => l.code === langCode)
        : null;

      if (sumLang) sumLang.textContent = langObj ? langObj.name : langCode;

      if (sumMode && window.SetupStepMode) {
        sumMode.textContent = mode === "standard"
          ? window.SetupStepMode.t("standard_title")
          : window.SetupStepMode.t("advanced_title");
      }

      if (sumStorage && window.SetupStepStorage) {
        sumStorage.textContent = storageOpt === "clean"
          ? window.SetupStepStorage.t("clean_title")
          : window.SetupStepStorage.t("custom_title");
      }

      if (sumComponents) sumComponents.textContent = `${components.length} moduli`;

      if (sumAssist && window.SetupStepAssistant) {
        const genderLabel = assistGender === "female"
          ? window.SetupStepAssistant.t("voice_female")
          : window.SetupStepAssistant.t("voice_male");
        sumAssist.textContent = `${assistName} (${genderLabel})`;
      }

      if (sumOwner) sumOwner.textContent = `${first} ${last}`.trim() || "—";
    }

    applyTranslations() {
      const lLang = document.querySelector('[data-i18n="setup.summary.lang"]');
      const lMode = document.querySelector('[data-i18n="setup.summary.mode"]');
      const lStorage = document.querySelector('[data-i18n="setup.summary.storage"]');
      const lAddons = document.querySelector('[data-i18n="setup.summary.addons"]');
      const lAssist = document.querySelector('[data-i18n="setup.summary.assistant"]');
      const lOwner = document.querySelector('[data-i18n="setup.summary.owner"]');

      if (lLang) lLang.textContent = this.t("summary_lang");
      if (lMode) lMode.textContent = this.t("summary_mode");
      if (lStorage) lStorage.textContent = this.t("summary_storage");
      if (lAddons) lAddons.textContent = this.t("summary_addons");
      if (lAssist) lAssist.textContent = this.t("summary_assistant");
      if (lOwner) lOwner.textContent = this.t("summary_owner");
    }

    async submit() {
      const storage = window.SetupStorage;
      const payload = {
        name: storage.get("ownerFirst") || "Proprietario",
        lang: storage.get("lang") || "it",
        assistant_name: storage.get("assistantName") || "Nuxiva",
        assistant_gender: storage.get("assistantGender") || "female",
        mode: storage.get("mode") || "standard",
        storage: storage.get("storage") || "clean",
        packages: storage.get("selectedComponents") || []
      };

      const res = await fetch("/api/setup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Nuxiva-Request": "1"
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || this.t("err_generic"));
      }

      storage.clear();
      window.location.href = "/";
    }

    init() {
      this.applyTranslations();
      this.render();
    }
  }

  window.SetupStepFinal = new StepFinal();
})();
