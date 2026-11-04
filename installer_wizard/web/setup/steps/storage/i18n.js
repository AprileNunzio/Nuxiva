(() => {
  "use strict";

  const dict = {
    it: {
      title: "Configurazione Archiviazione",
      sub: "Scegli come allocare lo spazio sul disco principale.",
      clean_title: "Cancella disco e installa",
      clean_sub: "Installazione pulita del sistema",
      clean_desc: "Il disco principale viene formattato e predisposto con la struttura di partizioni nativa di Nuxiva OS.",
      custom_title: "Partizionamento avanzato",
      custom_sub: "Configurazione manuale o dual-boot",
      custom_desc: "Scegli volumi LVM, tabelle GPT/MS-DOS personalizzate o punti di montaggio separati."
    },
    en: {
      title: "Storage Setup",
      sub: "Choose how to allocate space on your primary disk.",
      clean_title: "Erase disk and install",
      clean_sub: "Clean system setup",
      clean_desc: "The primary disk will be formatted and provisioned with native Nuxiva OS partitions.",
      custom_title: "Advanced partitioning",
      custom_sub: "Manual layout or dual-boot",
      custom_desc: "Select LVM volumes, custom GPT/MS-DOS tables or custom mount points."
    },
    es: {
      title: "Configuración de Almacenamiento",
      sub: "Elija cómo asignar el espacio en el disco principal.",
      clean_title: "Borrar disco e instalar",
      clean_sub: "Instalación limpia del sistema",
      clean_desc: "El disco principal se formateará con la estructura nativa de Nuxiva OS.",
      custom_title: "Particionamiento avanzado",
      custom_sub: "Configuración manual o dual-boot",
      custom_desc: "Elija volúmenes LVM o tablas de particiones personalizadas."
    },
    fr: {
      title: "Configuration du Stockage",
      sub: "Choisissez comment allouer l'espace sur le disque principal.",
      clean_title: "Effacer le disque et installer",
      clean_sub: "Installation propre du système",
      clean_desc: "Le disque principal est formaté avec la structure native de Nuxiva OS.",
      custom_title: "Partitionnement avancé",
      custom_sub: "Configuration manuelle ou dual-boot",
      custom_desc: "Choisissez des volumes LVM ou des points de montage personnalisés."
    }
  };

  window.SetupStepStorageI18n = { dict };
})();
