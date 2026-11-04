(() => {
  "use strict";

  class StepStorage {
    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = window.SetupStepStorageI18n.dict[lang] || window.SetupStepStorageI18n.dict.it;
      return dict[key] || key;
    }

    render() {
      const current = window.SetupStorage.get("storage") || "clean";
      document.querySelectorAll(".storage-card").forEach((card) => {
        const val = card.getAttribute("data-storage");
        if (val === current) {
          card.classList.add("os-card-selected");
        } else {
          card.classList.remove("os-card-selected");
        }
      });
    }

    applyTranslations() {
      const cleanTitle = document.querySelector('[data-i18n="setup.storage.clean_title"]');
      const cleanSub = document.querySelector('[data-i18n="setup.storage.clean_sub"]');
      const cleanDesc = document.querySelector('[data-i18n="setup.storage.clean_desc"]');
      const customTitle = document.querySelector('[data-i18n="setup.storage.custom_title"]');
      const customSub = document.querySelector('[data-i18n="setup.storage.custom_sub"]');
      const customDesc = document.querySelector('[data-i18n="setup.storage.custom_desc"]');

      if (cleanTitle) cleanTitle.textContent = this.t("clean_title");
      if (cleanSub) cleanSub.textContent = this.t("clean_sub");
      if (cleanDesc) cleanDesc.textContent = this.t("clean_desc");
      if (customTitle) customTitle.textContent = this.t("custom_title");
      if (customSub) customSub.textContent = this.t("custom_sub");
      if (customDesc) customDesc.textContent = this.t("custom_desc");
    }

    init() {
      document.querySelectorAll(".storage-card").forEach((card) => {
        card.addEventListener("click", () => {
          const val = card.getAttribute("data-storage");
          window.SetupStorage.set("storage", val);
          this.render();
        });
      });
      this.applyTranslations();
      this.render();
    }
  }

  window.SetupStepStorage = new StepStorage();
})();
