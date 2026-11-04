(() => {
  "use strict";

  class StepMode {
    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = window.SetupStepModeI18n.dict[lang] || window.SetupStepModeI18n.dict.it;
      return dict[key] || key;
    }

    render() {
      const currentMode = window.SetupStorage.get("mode") || "standard";
      document.querySelectorAll(".mode-card").forEach((card) => {
        const modeVal = card.getAttribute("data-mode");
        if (modeVal === currentMode) {
          card.classList.add("os-card-selected");
        } else {
          card.classList.remove("os-card-selected");
        }
      });
    }

    applyTranslations() {
      const stdTitle = document.querySelector('[data-i18n="setup.mode.standard_title"]');
      const stdSub = document.querySelector('[data-i18n="setup.mode.standard_sub"]');
      const stdDesc = document.querySelector('[data-i18n="setup.mode.standard_desc"]');
      const advTitle = document.querySelector('[data-i18n="setup.mode.advanced_title"]');
      const advSub = document.querySelector('[data-i18n="setup.mode.advanced_sub"]');
      const advDesc = document.querySelector('[data-i18n="setup.mode.advanced_desc"]');

      if (stdTitle) stdTitle.textContent = this.t("standard_title");
      if (stdSub) stdSub.textContent = this.t("standard_sub");
      if (stdDesc) stdDesc.textContent = this.t("standard_desc");
      if (advTitle) advTitle.textContent = this.t("advanced_title");
      if (advSub) advSub.textContent = this.t("advanced_sub");
      if (advDesc) advDesc.textContent = this.t("advanced_desc");
    }

    init() {
      document.querySelectorAll(".mode-card").forEach((card) => {
        card.addEventListener("click", () => {
          const modeVal = card.getAttribute("data-mode");
          window.SetupStorage.set("mode", modeVal);
          this.render();
        });
      });
      this.applyTranslations();
      this.render();
    }
  }

  window.SetupStepMode = new StepMode();
})();
