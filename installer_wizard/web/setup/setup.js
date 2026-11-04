(() => {
  "use strict";

  const storage = window.SetupStorage;

  const screens = [
    "screen-lang",
    "screen-wifi",
    "screen-components-core",
    "screen-components-opt",
    "screen-install",
    "screen-llm",
    "screen-owner",
    "screen-face",
    "screen-fingerprint",
    "screen-voice",
    "screen-assistant",
    "screen-final"
  ];

  let activeRev = null;
  let isRestarting = false;

  function showAlert(msg) {
    const alertBox = document.getElementById("status-alert");
    if (!alertBox) return;
    if (!msg) {
      alertBox.textContent = "";
      alertBox.classList.remove("show");
    } else {
      alertBox.textContent = msg;
      alertBox.classList.add("show");
    }
  }

  function updateStepper(step) {
    const stepperContainer = document.querySelector(".os-dialog-stepper");
    if (!stepperContainer) return;
    if (stepperContainer.children.length !== screens.length) {
      stepperContainer.innerHTML = "";
      for (let i = 0; i < screens.length; i++) {
        const dot = document.createElement("span");
        dot.className = "os-step-dot";
        stepperContainer.appendChild(dot);
      }
    }
    const dots = stepperContainer.querySelectorAll(".os-step-dot");
    dots.forEach((dot, idx) => {
      dot.className = "os-step-dot";
      if (idx === step) {
        dot.classList.add("is-active");
      } else if (idx < step) {
        dot.classList.add("is-completed");
      }
    });
  }

  function updateHero(step) {
    const titleEl = document.getElementById("setup-screen-title");
    const subEl = document.getElementById("setup-screen-subtitle");
    if (!titleEl || !subEl) return;

    const lang = storage.get("lang") || "it";

    if (step === 0 && window.SetupStepLang) {
      titleEl.textContent = window.SetupStepLang.t("title");
      subEl.textContent = window.SetupStepLang.t("sub");
    } else if (step === 1 && window.SetupStepWifi) {
      titleEl.textContent = window.SetupStepWifi.t("title");
      subEl.textContent = window.SetupStepWifi.t("sub");
    } else if ((step === 2 || step === 3) && window.SetupStepComponentsI18n) {
      const dict = window.SetupStepComponentsI18n.dict[lang] || window.SetupStepComponentsI18n.dict.it;
      if (step === 2) {
        titleEl.textContent = dict.core_title;
        subEl.textContent = dict.core_sub;
      } else {
        titleEl.textContent = dict.opt_title;
        subEl.textContent = dict.opt_sub;
      }
    } else if (step === 4 && window.SetupStepInstall) {
      titleEl.textContent = window.SetupStepInstall.t("title");
      subEl.textContent = window.SetupStepInstall.t("sub");
    } else if (step === 5 && window.SetupStepLlm) {
      titleEl.textContent = window.SetupStepLlm.t("title");
      subEl.textContent = window.SetupStepLlm.t("sub");
    } else if (step === 6 && window.SetupStepOwner) {
      titleEl.textContent = window.SetupStepOwner.t("title");
      subEl.textContent = window.SetupStepOwner.t("sub");
    } else if (step === 7 && window.SetupStepFace) {
      titleEl.textContent = window.SetupStepFace.t("title");
      subEl.textContent = window.SetupStepFace.t("sub");
    } else if (step === 8 && window.SetupStepFingerprint) {
      titleEl.textContent = window.SetupStepFingerprint.t("title");
      subEl.textContent = window.SetupStepFingerprint.t("sub");
    } else if (step === 9 && window.SetupStepVoice) {
      titleEl.textContent = window.SetupStepVoice.t("title");
      subEl.textContent = window.SetupStepVoice.t("sub");
    } else if (step === 10 && window.SetupStepAssistant) {
      titleEl.textContent = window.SetupStepAssistant.t("title");
      subEl.textContent = window.SetupStepAssistant.t("sub");
    } else if (step === 11 && window.SetupStepFinal) {
      titleEl.textContent = window.SetupStepFinal.t("title");
      subEl.textContent = window.SetupStepFinal.t("sub");
    }
  }

  function updateButtons(step) {
    const btnBack = document.getElementById("btn-back");
    const btnBackLabel = document.getElementById("btn-back-label");
    const btnNext = document.getElementById("btn-next-label");
    const btnNextIcon = document.getElementById("btn-next-icon");

    if (btnBack) {
      btnBack.style.visibility = step === 0 ? "hidden" : "visible";
    }

    if (btnBackLabel) {
      btnBackLabel.textContent = "Indietro";
    }

    const isLast = step === screens.length - 1;
    if (btnNext) {
      btnNext.textContent = isLast ? "Entra in Nuxiva OS" : "Avanti";
    }

    if (btnNextIcon) {
      if (isLast) {
        btnNextIcon.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
      } else {
        btnNextIcon.innerHTML = '<polyline points="9 18 15 12 9 6"></polyline>';
      }
    }
  }

  function showScreen(step) {
    showAlert("");
    screens.forEach((id, idx) => {
      const el = document.getElementById(id);
      if (el) {
        el.className = idx === step ? "setup-screen active" : "setup-screen";
      }
    });

    if (step === 0 && window.SetupStepLang) window.SetupStepLang.init();
    if (step === 1 && window.SetupStepWifi) window.SetupStepWifi.init();
    if (step === 2 && window.SetupStepComponents) window.SetupStepComponents.init();
    if (step === 3 && window.SetupStepComponents) window.SetupStepComponents.init();
    if (step === 4 && window.SetupStepInstall) window.SetupStepInstall.init();
    if (step === 5 && window.SetupStepLlm) window.SetupStepLlm.init();
    if (step === 6 && window.SetupStepOwner) window.SetupStepOwner.init();
    if (step === 7 && window.SetupStepFace) window.SetupStepFace.init();
    if (step === 8 && window.SetupStepFingerprint) window.SetupStepFingerprint.init();
    if (step === 9 && window.SetupStepVoice) window.SetupStepVoice.init();
    if (step === 10 && window.SetupStepAssistant) window.SetupStepAssistant.init();
    if (step === 11 && window.SetupStepFinal) window.SetupStepFinal.init();

    updateHero(step);
    updateButtons(step);
    updateStepper(step);
  }

  async function handleNext() {
    let currentStep = storage.get("step") || 0;

    if (currentStep === 1 && window.SetupStepWifi) {
      if (!window.SetupStepWifi.canProceed()) {
        showAlert(window.SetupStepWifi.t("err_must_connect"));
        return;
      }
    }

    if (currentStep === 6) {
      const first = (storage.get("ownerFirst") || "").trim();
      if (!first) {
        showAlert("Inserisci il tuo nome per procedere.");
        return;
      }
    }

    if (currentStep === screens.length - 1) {
      const btn = document.getElementById("btn-next");
      if (btn) btn.disabled = true;
      try {
        await window.SetupStepFinal.submit();
      } catch (err) {
        showAlert(err.message);
        if (btn) btn.disabled = false;
      }
      return;
    }

    currentStep++;
    storage.set("step", currentStep);
    showScreen(currentStep);
  }

  function handleBack() {
    let currentStep = storage.get("step") || 0;
    if (currentStep > 0) {
      currentStep--;
      storage.set("step", currentStep);
      showScreen(currentStep);
    }
  }

  function initTheme() {
    const savedTheme = storage.get("theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);

    const themeBtn = document.getElementById("btn-theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        storage.set("theme", next);
      });
    }
  }

  function showToast(text, duration = 3000) {
    const toast = document.getElementById("version-toast");
    if (!toast) return;
    toast.textContent = text;
    toast.classList.add("show");
    if (toast._timer) clearTimeout(toast._timer);
    if (duration > 0) {
      toast._timer = setTimeout(() => {
        toast.classList.remove("show");
      }, duration);
    }
  }

  function triggerUniversalReload(msg) {
    if (isRestarting) return;
    isRestarting = true;
    showToast(msg || "Aggiornamento applicato! Ricaricamento in corso...", 0);

    const checkInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/setup?t=${Date.now()}`);
        if (res.ok) {
          clearInterval(checkInterval);
          window.location.reload(true);
        }
      } catch (e) {
      }
    }, 1000);
  }

  function initLiveUpdateReloader() {
    async function pollLiveUpdate() {
      if (isRestarting) return;
      try {
        const res = await fetch(`/api/setup/update?t=${Date.now()}`);
        if (!res.ok) return;
        const data = await res.json();
        const serverRev = data.local_rev || data.rev;
        if (!serverRev) return;

        if (activeRev === null) {
          activeRev = serverRev;
          const label = document.getElementById("version-text");
          if (label) label.textContent = `v5.3 • ${serverRev.slice(0, 7)}`;
          return;
        }

        if (serverRev !== activeRev) {
          triggerUniversalReload("Nuovo aggiornamento applicato sul server! Ricaricamento di tutti i browser in corso...");
        }
      } catch (err) {
      }
    }

    setInterval(pollLiveUpdate, 3500);
  }

  function initVersionCheck() {
    const btn = document.getElementById("btn-version-check");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      if (btn.classList.contains("is-checking")) return;
      btn.classList.add("is-checking");
      showToast("Verifica nuovi commit online in corso...", 0);

      try {
        const res = await fetch("/api/setup/update/sync", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Nuxiva-Request": "1"
          }
        });

        if (!res.ok) {
          showToast("Errore durante la verifica con il server.");
          btn.classList.remove("is-checking");
          return;
        }

        const data = await res.json();
        if (data.applied) {
          triggerUniversalReload("Nuovo aggiornamento applicato! Riavvio server e ricaricamento browser...");
        } else if (data.uptodate) {
          showToast("Nuxiva OS è già aggiornato all'ultimo commit.");
          btn.classList.remove("is-checking");
        } else if (data.error) {
          showToast(data.error);
          btn.classList.remove("is-checking");
        } else {
          showToast("Nessun nuovo commit disponibile.");
          btn.classList.remove("is-checking");
        }
      } catch (err) {
        showToast("Impossibile verificare gli aggiornamenti.");
        btn.classList.remove("is-checking");
      }
    });
  }

  window.SetupApp = {
    onLangChanged() {
      const step = storage.get("step") || 0;
      updateHero(step);
      updateButtons(step);
      if (window.SetupStepWifi) window.SetupStepWifi.applyTranslations();
      if (window.SetupStepComponents) window.SetupStepComponents.render();
      if (window.SetupStepAssistant) window.SetupStepAssistant.applyTranslations();
      if (window.SetupStepOwner) window.SetupStepOwner.applyTranslations();
      if (window.SetupStepFinal) window.SetupStepFinal.applyTranslations();
    }
  };

  async function boot() {
    initTheme();
    initVersionCheck();
    initLiveUpdateReloader();

    const btnNext = document.getElementById("btn-next");
    const btnBack = document.getElementById("btn-back");

    if (btnNext) btnNext.addEventListener("click", handleNext);
    if (btnBack) btnBack.addEventListener("click", handleBack);

    try {
      const res = await fetch(`/api/setup?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        if (data.needed === false) {
          window.location.href = "/";
          return;
        }
      }
    } catch (e) {}

    const currentStep = storage.get("step") || 0;
    showScreen(currentStep);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();