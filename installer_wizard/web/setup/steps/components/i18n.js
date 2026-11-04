(() => {
  "use strict";

  const packages = [
    { id: "voice", title: "Voce Neurale Offline", desc: "Sintesi vocale locale ad alta fedeltà con risposta immediata.", size: "1.0 GB", core: true },
    { id: "ear", title: "Ascolto & Wake-Word", desc: "Riconoscimento vocale per attivazione a voce e comandi diretti.", size: "1.5 GB", core: false },
    { id: "vision", title: "Visione Artificiale", desc: "Riconoscimento volti e ambiente locale tramite webcam e telecamere.", size: "1.0 GB", core: false },
    { id: "sandbox", title: "Sandbox di Sicurezza", desc: "Isolamento sicuro dei comandi e dell'esecuzione codice utente.", size: "0.6 GB", core: true },
    { id: "brain_local", title: "Cervello LLM Locale", desc: "Motore di inferenza Ollama integrato per privacy totale.", size: "8.0 GB", core: false }
  ];

  const dict = {
    it: {
      title: "Componenti Aggiuntivi",
      sub: "Seleziona i moduli intelligenti da installare ed eseguire sul dispositivo."
    },
    en: {
      title: "Optional Components",
      sub: "Select the intelligent modules to provision on this host."
    },
    es: {
      title: "Componentes Opcionales",
      sub: "Seleccione los módulos inteligentes para aprovisionar."
    },
    fr: {
      title: "Composants Optionnels",
      sub: "Sélectionnez les modules intelligents à provisionner."
    }
  };

  window.SetupStepComponentsI18n = { packages, dict };
})();
