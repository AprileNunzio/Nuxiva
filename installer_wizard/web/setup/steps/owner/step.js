(() => {
  "use strict";

  class StepOwner {
    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = window.SetupStepOwnerI18n.dict[lang] || window.SetupStepOwnerI18n.dict.it;
      return dict[key] || key;
    }

    render() {
      const first = window.SetupStorage.get("ownerFirst") || "";
      const last = window.SetupStorage.get("ownerLast") || "";

      const firstInp = document.getElementById("cfg-owner-name");
      const lastInp = document.getElementById("cfg-owner-last");

      if (firstInp && !firstInp.value) firstInp.value = first;
      if (lastInp && !lastInp.value) lastInp.value = last;
    }

    applyTranslations() {
      const firstLbl = document.querySelector('[data-i18n="setup.owner.first"]');
      const lastLbl = document.querySelector('[data-i18n="setup.owner.last"]');

      if (firstLbl) firstLbl.textContent = this.t("first_label");
      if (lastLbl) lastLbl.textContent = this.t("last_label");
    }

    init() {
      const firstInp = document.getElementById("cfg-owner-name");
      const lastInp = document.getElementById("cfg-owner-last");

      if (firstInp) {
        firstInp.addEventListener("input", (e) => {
          window.SetupStorage.set("ownerFirst", e.target.value.trim());
        });
      }

      if (lastInp) {
        lastInp.addEventListener("input", (e) => {
          window.SetupStorage.set("ownerLast", e.target.value.trim());
        });
      }

      this.applyTranslations();
      this.render();
    }
  }

  window.SetupStepOwner = new StepOwner();
})();
