(() => {
  "use strict";

  const packagesCore = [
    { id: "voice", title: "Voce Neurale Offline", desc: "Sintesi vocale locale ad alta fedeltà con risposta immediata.", size: "1.0 GB", core: true },
    { id: "sandbox", title: "Sandbox di Sicurezza", desc: "Isolamento sicuro dei comandi e dell'esecuzione codice utente.", size: "0.6 GB", core: true }
  ];

  const packagesOpt = [
    { id: "ear", title: "Ascolto & Wake-Word", desc: "Riconoscimento vocale per attivazione a voce e comandi diretti.", size: "1.5 GB", core: false },
    { id: "vision", title: "Visione Artificiale", desc: "Riconoscimento volti e ambiente locale tramite webcam e telecamere.", size: "1.0 GB", core: false },
    { id: "brain_local", title: "Cervello LLM Locale", desc: "Motore di inferenza Ollama integrato per privacy totale.", size: "8.0 GB", core: false }
  ];

  const packages = [...packagesCore, ...packagesOpt];

  const dict = {
    it: {
      core_title: "Componenti di Sistema",
      core_sub: "Moduli essenziali preconfigurati per garantire sicurezza e integrità del sistema.",
      opt_title: "Componenti Aggiuntivi",
      opt_sub: "Seleziona i moduli facoltativi da installare ed eseguire sul dispositivo.",
      badge_core: "Obbligatorio",
      badge_opt: "Opzionale"
    },
    en: {
      core_title: "System Components",
      core_sub: "Essential modules preconfigured to ensure system security and stability.",
      opt_title: "Optional Addons",
      opt_sub: "Select optional intelligent modules to install and run on this device.",
      badge_core: "Required",
      badge_opt: "Optional"
    },
    es: {
      core_title: "Componentes del Sistema",
      core_sub: "Módulos esenciales preconfigurados para garantizar la seguridad del sistema.",
      opt_title: "Componentes Opcionales",
      opt_sub: "Seleccione los módulos opcionales para instalar y ejecutar en el dispositivo.",
      badge_core: "Obligatorio",
      badge_opt: "Opcional"
    },
    fr: {
      core_title: "Composants Système",
      core_sub: "Modules essentiels préconfigurés pour garantir la sécurité du système.",
      opt_title: "Composants Optionnels",
      opt_sub: "Sélectionnez les modules optionnels à installer et exécuter sur l'appareil.",
      badge_core: "Obligatoire",
      badge_opt: "Optionnel"
    }
  };

  window.SetupStepComponentsI18n = { packagesCore, packagesOpt, packages, dict };
})();
