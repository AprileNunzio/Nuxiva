(() => {
  "use strict";

  const languages = [
    { code: "it", name: "Italiano", sub: "Italian", badge: "IT" },
    { code: "en", name: "English", sub: "English (US)", badge: "EN" },
    { code: "es", name: "Español", sub: "Spanish", badge: "ES" },
    { code: "fr", name: "Français", sub: "French", badge: "FR" },
    { code: "de", name: "Deutsch", sub: "German", badge: "DE" },
    { code: "pt", name: "Português", sub: "Portuguese", badge: "PT" },
    { code: "zh", name: "简体中文", sub: "Chinese", badge: "ZH" },
    { code: "ja", name: "日本語", sub: "Japanese", badge: "JA" }
  ];

  const dict = {
    it: {
      title: "Lingua",
      sub: "Scegli la lingua principale per l'interfaccia e i modelli vocali.",
      search_placeholder: "Cerca lingua...",
      no_results: "Nessuna lingua trovata"
    },
    en: {
      title: "Language",
      sub: "Choose your primary language for the interface and voice models.",
      search_placeholder: "Search language...",
      no_results: "No language found"
    },
    es: {
      title: "Idioma",
      sub: "Elija el idioma principal para la interfaz y los modelos de voz.",
      search_placeholder: "Buscar idioma...",
      no_results: "No se encontraron idiomas"
    },
    fr: {
      title: "Langue",
      sub: "Choisissez la langue principale pour l'interface et les modèles vocaux.",
      search_placeholder: "Rechercher une langue...",
      no_results: "Aucune langue trouvée"
    }
  };

  window.SetupStepLangI18n = { languages, dict };
})();
