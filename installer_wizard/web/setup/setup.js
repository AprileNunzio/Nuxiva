(() => {
  "use strict";

  const storage = window.SetupStorage;

  const screens = [
    "screen-lang",
    "screen-mode",
    "screen-storage",
    "screen-components-core",
    "screen-components-opt",
    "screen-assistant",
    "screen-owner",
    "screen-final"
  ];

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
    const dots = document.querySelectorAll(".os-step-dot");
    if (!dots || dots.length === 0) return;
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

    if (step === 0 && window.SetupStepLang) {
      titleEl.textContent = window.SetupStepLang.t("title");
      subEl.textContent = window.SetupStepLang.t("sub");
    } else if (step === 1 && window.SetupStepMode) {
      titleEl.textContent = window.SetupStepMode.t("title");
      subEl.textContent = window.SetupStepMode.t("sub");
    } else if (step === 2 && window.SetupStepStorage) {
      titleEl.textContent = window.SetupStepStorage.t("title");
      subEl.textContent = window.SetupStepStorage.t("sub");
    } else if (step === 3 && window.SetupStepComponentsI18n) {
      const lang = storage.get("lang") || "it";
      const dict = window.SetupStepComponentsI18n.dict[lang] || window.SetupStepComponentsI18n.dict.it;
      titleEl.textContent = dict.core_title || "Componenti di Sistema";
      subEl.textContent = dict.core_sub || "Moduli essenziali preconfigurati per garantire sicurezza e integrità del sistema.";
    } else if (step === 4 && window.SetupStepComponentsI18n) {
      const lang = storage.get("lang") || "it";
      const dict = window.SetupStepComponentsI18n.dict[lang] || window.SetupStepComponentsI18n.dict.it;
      titleEl.textContent = dict.opt_title || "Componenti Aggiuntivi";
      subEl.textContent = dict.opt_sub || "Seleziona i moduli facoltativi da installare ed eseguire sul dispositivo.";
    } else if (step === 5 && window.SetupStepAssistant) {
      titleEl.textContent = window.SetupStepAssistant.t("title");
      subEl.textContent = window.SetupStepAssistant.t("sub");
    } else if (step === 6 && window.SetupStepOwner) {
      titleEl.textContent = window.SetupStepOwner.t("title");
      subEl.textContent = window.SetupStepOwner.t("sub");
    } else if (step === 7 && window.SetupStepFinal) {
      titleEl.textContent = window.SetupStepFinal.t("title");
      subEl.textContent = window.SetupStepFinal.t("sub");
    }
  }

  function updateButtons(step) {
    const btnBack = document.getElementById("btn-back");
    const btnBackLabel = document.getElementById("btn-back-label");
    const btnNext = document.getElementById("btn-next-label");
    const btnNextIcon = document.getElementById("btn-next-icon");

    const lang = storage.get("lang") || "it";
    const dict = (window.SetupStepFinalI18n && window.SetupStepFinalI18n.dict[lang]) || {};

    if (btnBack) {
      btnBack.style.visibility = step === 0 ? "hidden" : "visible";
    }

    if (btnBackLabel) {
      btnBackLabel.textContent = dict.btn_back || "Indietro";
    }

    const isLast = step === screens.length - 1;
    if (btnNext) {
      btnNext.textContent = isLast ? (dict.btn_complete || "Entra in Nuxiva OS") : (dict.btn_next || "Avanti");
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
    if (step === 1 && window.SetupStepMode) window.SetupStepMode.init();
    if (step === 2 && window.SetupStepStorage) window.SetupStepStorage.init();
    if (step === 3 && window.SetupStepComponents) window.SetupStepComponents.init();
    if (step === 4 && window.SetupStepComponents) window.SetupStepComponents.init();
    if (step === 5 && window.SetupStepAssistant) window.SetupStepAssistant.init();
    if (step === 6 && window.SetupStepOwner) window.SetupStepOwner.init();
    if (step === 7 && window.SetupStepFinal) window.SetupStepFinal.init();

    updateHero(step);
    updateButtons(step);
    updateStepper(step);
  }

  async function handleNext() {
    let currentStep = storage.get("step") || 0;

    if (currentStep === 6) {
      const first = (storage.get("ownerFirst") || "").trim();
      if (!first) {
        const lang = storage.get("lang") || "it";
        const errText = (window.SetupStepOwnerI18n && window.SetupStepOwnerI18n.dict[lang] && window.SetupStepOwnerI18n.dict[lang].err_required)
          || "Inserisci il tuo nome per procedere.";
        showAlert(errText);
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

  function initVersionCheck() {
    const btn = document.getElementById("btn-version-check");
    const label = document.getElementById("version-text");
    if (!btn) return;

    fetch(`/api/setup/update?t=${Date.now()}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.rev && label) {
          label.textContent = `v5.3 • ${data.rev.slice(0, 7)}`;
        }
      })
      .catch(() => {});

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
          showToast("Nuovo aggiornamento applicato! Ricaricamento...", 0);
          setTimeout(() => {
            window.location.reload();
          }, 1500);
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
    onLangChanged(newLang) {
      const step = storage.get("step") || 0;
      updateHero(step);
      updateButtons(step);
      if (window.SetupStepMode) window.SetupStepMode.applyTranslations();
      if (window.SetupStepStorage) window.SetupStepStorage.applyTranslations();
      if (window.SetupStepComponents) window.SetupStepComponents.render();
      if (window.SetupStepAssistant) window.SetupStepAssistant.applyTranslations();
      if (window.SetupStepOwner) window.SetupStepOwner.applyTranslations();
      if (window.SetupStepFinal) window.SetupStepFinal.applyTranslations();
    }
  };

  async function boot() {
    initTheme();
    initVersionCheck();

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
    } catch (e) {
    }

    const currentStep = storage.get("step") || 0;
    showScreen(currentStep);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
