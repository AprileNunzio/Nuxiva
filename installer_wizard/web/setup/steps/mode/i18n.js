(() => {
  "use strict";

  const dict = {
    it: {
      title: "Modalità di Installazione",
      sub: "Seleziona la tipologia di configurazione del sistema.",
      standard_title: "Installazione Standard",
      standard_sub: "Consigliata per la maggior parte dei sistemi",
      standard_desc: "Configurazione automatica delle partizioni e del filesystem con parametri ottimali per le prestazioni.",
      advanced_title: "Installazione Avanzata",
      advanced_sub: "Per esperti e server dedicati",
      advanced_desc: "Personalizzazione delle partizioni di sistema, selezione mirata dei componenti e isolamento hardware."
    },
    en: {
      title: "Installation Mode",
      sub: "Select your system configuration mode.",
      standard_title: "Standard Installation",
      standard_sub: "Recommended for most systems",
      standard_desc: "Automatic partition and filesystem configuration with optimal defaults.",
      advanced_title: "Advanced Installation",
      advanced_sub: "For experts and dedicated servers",
      advanced_desc: "Custom partition tables, selective component provisioning and hardware isolation."
    },
    es: {
      title: "Modo de Instalación",
      sub: "Seleccione el tipo de configuración del sistema.",
      standard_title: "Instalación Estándar",
      standard_sub: "Recomendada para la mayoría de sistemas",
      standard_desc: "Configuración automática de particiones con parámetros óptimos.",
      advanced_title: "Instalación Avanzada",
      advanced_sub: "Para expertos y servidores dedicados",
      advanced_desc: "Personalización de particiones y aprovisionamiento selectivo de componentes."
    },
    fr: {
      title: "Mode d'Installation",
      sub: "Sélectionnez le type de configuration du système.",
      standard_title: "Installation Standard",
      standard_sub: "Recommandée pour la plupart des systèmes",
      standard_desc: "Configuration automatique des partitions avec des paramètres optimaux.",
      advanced_title: "Installation Avancée",
      advanced_sub: "Pour experts et serveurs dédiés",
      advanced_desc: "Personnalisation des partitions et sélection modulaire des composants."
    }
  };

  window.SetupStepModeI18n = { dict };
})();
