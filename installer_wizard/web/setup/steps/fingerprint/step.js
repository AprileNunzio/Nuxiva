(() => {
  "use strict";

  class StepFingerprint {
    constructor() {
      this.currentTouch = 0;
      this.totalTouches = 3;
      this.hasSensor = false;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepFingerprintI18n && window.SetupStepFingerprintI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    async checkHardwareSensor() {
      if (window.PublicKeyCredential && PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable) {
        try {
          const avail = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
          return Boolean(avail);
        } catch (e) {}
      }
      return false;
    }

    handleTouch() {
      if (this.currentTouch >= this.totalTouches) return;
      this.currentTouch++;

      for (let i = 1; i <= this.totalTouches; i++) {
        const chip = document.getElementById(`fp-chip-${i}`);
        if (!chip) continue;
        if (i < this.currentTouch) {
          chip.className = "os-fp-step-chip is-done";
        } else if (i === this.currentTouch) {
          chip.className = "os-fp-step-chip is-active";
        } else {
          chip.className = "os-fp-step-chip";
        }
      }

      const metaMinutiae = document.getElementById("fp-meta-minutiae");
      const metaVector = document.getElementById("fp-meta-vector");
      if (metaMinutiae) metaMinutiae.textContent = `Minutiae: ${this.currentTouch * 28}`;
      if (metaVector) metaVector.textContent = `FMR: 0.001% (Touch ${this.currentTouch}/3)`;

      if (this.currentTouch >= this.totalTouches) {
        const target = document.getElementById("fp-sensor-target");
        if (target) target.classList.add("is-scanned");
        const promptEl = document.getElementById("fp-prompt-text");
        if (promptEl) {
          promptEl.textContent = this.t("success_badge");
          promptEl.style.color = "#10b981";
        }
        window.SetupStorage.set("fingerprintEnrolled", true);
      }
    }

    async init() {
      this.hasSensor = await this.checkHardwareSensor();
      const scannerCard = document.getElementById("fp-scanner-card");
      const noSensorCard = document.getElementById("fp-no-sensor-card");

      if (!this.hasSensor) {
        if (scannerCard) scannerCard.style.display = "none";
        if (noSensorCard) noSensorCard.classList.add("show");
        window.SetupStorage.set("fingerprintEnrolled", false);
        return;
      }

      if (scannerCard) scannerCard.style.display = "flex";
      if (noSensorCard) noSensorCard.classList.remove("show");

      this.currentTouch = 0;
      const target = document.getElementById("fp-sensor-target");
      if (target) {
        target.addEventListener("click", () => this.handleTouch());
      }
    }
  }

  window.SetupStepFingerprint = new StepFingerprint();
})();
