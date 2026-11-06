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

    async loadProviders(select) {
      const saved = window.SetupStorage.get("cloud_provider") || "";
      try {
        const res = await fetch(`/api/setup?t=${Date.now()}`, { credentials: "same-origin" });
        const data = res.ok ? await res.json() : {};
        const clouds = data && typeof data.clouds === "object" && data.clouds ? data.clouds : {};
        const entries = Object.entries(clouds).filter(([id, name]) => typeof id === "string" && typeof name === "string");
        if (entries.length) {
          select.replaceChildren(...entries.map(([id, name]) => {
            const option = document.createElement("option");
            option.value = id;
            option.textContent = name;
            return option;
          }));
        }
      } catch (err) {
        console.warn("setup: cloud providers unavailable", err);
      }
      const ids = [...select.options].map((o) => o.value);
      select.value = ids.includes(saved) ? saved : ids[0] || "";
      window.SetupStorage.set("cloud_provider", select.value);
    }

    feedback(el, key, ok) {
      el.className = `os-llm-feedback ${ok ? "is-ok" : "is-err"}`;
      el.textContent = this.t(key);
    }

    async testKey(button, el) {
      const key = (document.getElementById("llm-cloud-key")?.value || "").trim();
      const provider = document.getElementById("llm-cloud-provider")?.value || "";
      if (!key) {
        this.feedback(el, "key_missing", false);
        return;
      }
      button.disabled = true;
      this.feedback(el, "key_checking", true);
      try {
        const res = await fetch("/api/setup/cloud/test", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
          body: JSON.stringify({ cloud_provider: provider, cloud_key: key })
        });
        const data = res.ok ? await res.json() : {};
        this.feedback(el, data.ok === true ? "key_ok" : "key_err", data.ok === true);
      } catch (err) {
        this.feedback(el, "key_err", false);
      } finally {
        button.disabled = false;
      }
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
        provSelect.addEventListener("change", (e) => {
          window.SetupStorage.set("cloud_provider", e.target.value);
        });
        this.loadProviders(provSelect);
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
        btnTestCloud.addEventListener("click", () => this.testKey(btnTestCloud, fbCloud));
      }
    }
  }

  window.SetupStepLlm = new StepLlm();
})();
