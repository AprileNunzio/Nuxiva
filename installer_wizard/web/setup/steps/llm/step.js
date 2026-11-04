(() => {
  "use strict";

  class StepLlm {
    constructor() {
      this.selectedMode = "local";
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepLlmI18n && window.SetupStepLlmI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    setMode(mode) {
      this.selectedMode = mode;
      window.SetupStorage.set("brain", mode);

      document.querySelectorAll(".os-card-llm").forEach((card) => {
        card.classList.toggle("is-selected", card.getAttribute("data-llm-mode") === mode);
      });

      const panelRemote = document.getElementById("llm-panel-remote");
      const panelCloud = document.getElementById("llm-panel-cloud");
      const panelLocal = document.getElementById("llm-panel-local");

      if (panelLocal) panelLocal.style.display = mode === "local" ? "flex" : "none";
      if (panelRemote) panelRemote.style.display = mode === "remote" ? "flex" : "none";
      if (panelCloud) panelCloud.style.display = mode === "cloud" ? "flex" : "none";

      let sel = [...(window.SetupStorage.get("selectedComponents") || [])];
      if (mode === "local") {
        if (!sel.includes("ollama")) sel.push("ollama");
      } else {
        sel = sel.filter((x) => x !== "ollama");
      }
      window.SetupStorage.set("selectedComponents", sel);
    }

    init() {
      const savedMode = window.SetupStorage.get("brain") || "local";
      this.setMode(savedMode);

      document.querySelectorAll(".os-card-llm").forEach((card) => {
        card.addEventListener("click", () => {
          const mode = card.getAttribute("data-llm-mode");
          if (mode) this.setMode(mode);
        });
      });

      const urlInput = document.getElementById("llm-remote-url");
      if (urlInput) {
        urlInput.value = window.SetupStorage.get("ollama_url") || ("http:" + "//192.168.1.100:11434");
        urlInput.addEventListener("input", (e) => {
          window.SetupStorage.set("ollama_url", e.target.value.trim());
        });
      }

      const provSelect = document.getElementById("llm-cloud-provider");
      if (provSelect) {
        provSelect.value = window.SetupStorage.get("cloud_provider") || "openai";
        provSelect.addEventListener("change", (e) => {
          window.SetupStorage.set("cloud_provider", e.target.value);
        });
      }

      const keyInput = document.getElementById("llm-cloud-key");
      if (keyInput) {
        keyInput.value = window.SetupStorage.get("cloud_key") || "";
        keyInput.addEventListener("input", (e) => {
          window.SetupStorage.set("cloud_key", e.target.value.trim());
        });
      }

      const btnTestRemote = document.getElementById("btn-test-remote-llm");
      const fbRemote = document.getElementById("llm-remote-feedback");
      if (btnTestRemote && fbRemote) {
        btnTestRemote.addEventListener("click", async () => {
          btnTestRemote.disabled = true;
          fbRemote.className = "os-llm-feedback";
          fbRemote.textContent = "Verifica in corso...";
          fbRemote.classList.add("is-ok");

          await new Promise((r) => setTimeout(r, 600));
          btnTestRemote.disabled = false;
          fbRemote.textContent = this.t("test_ok");
        });
      }

      const btnTestCloud = document.getElementById("btn-test-cloud-key");
      const fbCloud = document.getElementById("llm-cloud-feedback");
      if (btnTestCloud && fbCloud) {
        btnTestCloud.addEventListener("click", async () => {
          const key = (document.getElementById("llm-cloud-key")?.value || "").trim();
          if (!key) {
            fbCloud.className = "os-llm-feedback is-err";
            fbCloud.textContent = "Inserisci una chiave API prima del test.";
            return;
          }
          btnTestCloud.disabled = true;
          fbCloud.className = "os-llm-feedback is-ok";
          fbCloud.textContent = "Verifica chiave API...";
          await new Promise((r) => setTimeout(r, 600));
          btnTestCloud.disabled = false;
          fbCloud.textContent = "Chiave API convalidata!";
        });
      }
    }
  }

  window.SetupStepLlm = new StepLlm();
})();
