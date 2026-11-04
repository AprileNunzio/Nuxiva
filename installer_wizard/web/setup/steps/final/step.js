(() => {
  "use strict";

  class StepFinal {
    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepFinalI18n && window.SetupStepFinalI18n.dict[lang]) || (window.SetupStepFinalI18n && window.SetupStepFinalI18n.dict.it) || {};
      return dict[key] || key;
    }

    render() {
      const storage = window.SetupStorage;
      const langCode = storage.get("lang") || "it";
      const components = storage.get("selectedComponents") || [];
      const brain = storage.get("brain") || "local";
      const assistName = storage.get("assistantName") || "Nuxiva";
      const assistGender = storage.get("assistantGender") || "female";
      const first = storage.get("ownerFirst") || "Proprietario";
      const last = storage.get("ownerLast") || "";
      const faceDone = Boolean(storage.get("faceEnrolled"));
      const fpDone = Boolean(storage.get("fingerprintEnrolled"));
      const micDev = storage.get("micDevice") || "Predefinito";

      const sumLang = document.getElementById("sum-lang");
      const sumComponents = document.getElementById("sum-components");
      const sumLlm = document.getElementById("sum-llm");
      const sumOwner = document.getElementById("sum-owner");
      const sumFace = document.getElementById("sum-face");
      const sumFp = document.getElementById("sum-fingerprint");
      const sumVoice = document.getElementById("sum-voice");
      const sumAssist = document.getElementById("sum-assistant");

      const langObj = (window.SetupStepLangI18n && window.SetupStepLangI18n.languages)
        ? window.SetupStepLangI18n.languages.find((l) => l.code === langCode)
        : null;

      if (sumLang) sumLang.textContent = langObj ? langObj.name : langCode;
      if (sumComponents) sumComponents.textContent = `${components.length} moduli attivi`;

      if (sumLlm) {
        sumLlm.textContent = brain === "local" ? "Locale (Ollama)" : brain === "remote" ? "Remoto (Server)" : "Cloud API";
      }

      if (sumOwner) sumOwner.textContent = `${first} ${last}`.trim() || "—";
      if (sumFace) sumFace.textContent = faceDone ? "Configurato (3 Punti)" : "Non attivo";
      if (sumFp) sumFp.textContent = fpDone ? "Registrata" : "Non rilevata";
      if (sumVoice) sumVoice.textContent = micDev === "default" ? "Microfono Attivo" : micDev;

      if (sumAssist) {
        const gLabel = assistGender === "female" ? "Femminile" : assistGender === "male" ? "Maschile" : "Sintetico";
        sumAssist.textContent = `${assistName} (${gLabel})`;
      }
    }

    applyTranslations() {
      this.render();
    }

    async submit() {
      const storage = window.SetupStorage;
      const payload = {
        name: storage.get("ownerFirst") || "Proprietario",
        last_name: storage.get("ownerLast") || "",
        lang: storage.get("lang") || "it",
        assistant_name: storage.get("assistantName") || "Nuxiva",
        assistant_gender: storage.get("assistantGender") || "female",
        brain: storage.get("brain") || "local",
        ollama_url: storage.get("ollama_url") || "",
        cloud_provider: storage.get("cloud_provider") || "",
        cloud_key: storage.get("cloud_key") || "",
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
        throw new Error(errData.detail || "Errore durante la finalizzazione del setup.");
      }

      window.location.href = "/";
    }

    init() {
      this.render();
    }
  }

  window.SetupStepFinal = new StepFinal();
})();
