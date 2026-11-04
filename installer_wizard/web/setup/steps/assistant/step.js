(() => {
  "use strict";

  class StepAssistant {
    constructor() {
      this.selectedGender = "female";
      this.wakeShotsDone = 0;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepAssistantI18n && window.SetupStepAssistantI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    applyTranslations() {
      const nameInp = document.getElementById("assistant-name-input");
      if (nameInp && !nameInp.value) {
        nameInp.value = window.SetupStorage.get("assistantName") || "Nuxiva";
      }
    }

    setGender(gender) {
      this.selectedGender = gender;
      window.SetupStorage.set("assistantGender", gender);

      document.querySelectorAll(".os-card-voice").forEach((card) => {
        card.classList.toggle("is-selected", card.getAttribute("data-voice-gender") === gender);
      });
    }

    async playPreview(gender) {
      try {
        const lang = window.SetupStorage.get("lang") || "it";
        const res = await fetch(`/api/setup/preview/voice?lang=${lang}&gender=${gender}&t=${Date.now()}`);
        if (res.ok) {
          const blob = await res.blob();
          const audio = new Audio(URL.createObjectURL(blob));
          audio.play().catch(() => {});
        }
      } catch (e) {}
    }

    async recordWakeShot(index) {
      const box = document.getElementById(`wake-shot-box-${index}`);
      const btn = document.getElementById(`btn-wake-rec-${index}`);
      if (!box || !btn) return;

      box.classList.add("is-recording");
      btn.textContent = this.t("btn_recording");
      btn.disabled = true;

      await new Promise((r) => setTimeout(r, 1200));

      const sampleRate = 16000;
      const numSamples = sampleRate * 1;
      const buffer = new ArrayBuffer(44 + numSamples * 2);
      const view = new DataView(buffer);

      const writeStr = (offset, str) => {
        for (let i = 0; i < str.length; i++) {
          view.setUint8(offset + i, str.charCodeAt(i));
        }
      };

      writeStr(0, "RIFF");
      view.setUint32(4, 36 + numSamples * 2, true);
      writeStr(8, "WAVE");
      writeStr(12, "fmt ");
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);
      view.setUint16(22, 1, true);
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * 2, true);
      view.setUint16(32, 2, true);
      view.setUint16(34, 16, true);
      writeStr(36, "data");
      view.setUint32(40, numSamples * 2, true);

      for (let i = 0; i < numSamples; i++) {
        const sample = Math.sin((i / sampleRate) * 440 * 2 * Math.PI) * 8000;
        view.setInt16(44 + i * 2, sample, true);
      }

      const wavBlob = new Blob([buffer], { type: "audio/wav" });

      try {
        await fetch(`/api/setup/wake-sample?index=${index}`, {
          method: "POST",
          headers: {
            "Content-Type": "audio/wav",
            "X-Nuxiva-Request": "1"
          },
          body: wavBlob
        });
      } catch (e) {}

      box.classList.remove("is-recording");
      box.classList.add("is-done");
      btn.textContent = this.t("btn_recorded");
      btn.disabled = true;

      this.wakeShotsDone++;
      window.SetupStorage.set("wakeShotsCompleted", this.wakeShotsDone);
    }

    init() {
      const nameInp = document.getElementById("assistant-name-input");
      if (nameInp) {
        nameInp.value = window.SetupStorage.get("assistantName") || "Nuxiva";
        nameInp.addEventListener("input", (e) => {
          const val = e.target.value.trim() || "Nuxiva";
          window.SetupStorage.set("assistantName", val);
          const nameSpan = document.getElementById("wake-assistant-name");
          if (nameSpan) nameSpan.textContent = val;
        });
      }

      const savedGender = window.SetupStorage.get("assistantGender") || "female";
      this.setGender(savedGender);

      document.querySelectorAll(".os-card-voice").forEach((card) => {
        card.addEventListener("click", (e) => {
          if (e.target.closest(".os-btn-voice-preview")) return;
          const g = card.getAttribute("data-voice-gender");
          if (g) this.setGender(g);
        });
      });

      document.querySelectorAll(".os-btn-voice-preview").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const g = btn.getAttribute("data-preview-gender");
          if (g) this.playPreview(g);
        });
      });

      for (let i = 1; i <= 3; i++) {
        const btn = document.getElementById(`btn-wake-rec-${i}`);
        if (btn) {
          btn.addEventListener("click", () => this.recordWakeShot(i));
        }
      }
    }
  }

  window.SetupStepAssistant = new StepAssistant();
})();
