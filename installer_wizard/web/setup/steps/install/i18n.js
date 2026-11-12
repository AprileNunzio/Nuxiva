(() => {
  "use strict";

  const dict = {
    it: {
      title: "Installazione Componenti",
      sub: "Download, verifica crittografica e configurazione dei moduli selezionati.",
      overall_progress: "Avanzamento Globale",
      status_pending: "In attesa",
      status_downloading: "Download in corso...",
      status_extracting: "Estrazione e verifica...",
      status_completed: "Pronto",
      ready_badge: "Tutti i moduli sono stati installati con successo."
    },
    en: {
      title: "Installing Components",
      sub: "Downloading, cryptographically verifying and configuring selected modules.",
      overall_progress: "Overall Progress",
      status_pending: "Pending",
      status_downloading: "Downloading...",
      status_extracting: "Extracting and verifying...",
      status_completed: "Ready",
      ready_badge: "All selected modules have been installed successfully."
    },
    es: {
      title: "Instalación de Componentes",
      sub: "Descarga, verificación criptográfica y configuración de los módulos seleccionados.",
      overall_progress: "Progreso Global",
      status_pending: "En espera",
      status_downloading: "Descargando...",
      status_extracting: "Extrayendo y verificando...",
      status_completed: "Listo",
      ready_badge: "Todos los módulos seleccionados se instalaron correctamente."
    },
    fr: {
      title: "Installation des Composants",
      sub: "Téléchargement, vérification cryptographique et configuration des modules.",
      overall_progress: "Progression Globale",
      status_pending: "En attente",
      status_downloading: "Téléchargement...",
      status_extracting: "Extraction et vérification...",
      status_completed: "Prêt",
      ready_badge: "Tous les composants sélectionnés ont été installés avec succès."
    }
  };

  window.SetupStepInstallI18n = { dict };
})();
