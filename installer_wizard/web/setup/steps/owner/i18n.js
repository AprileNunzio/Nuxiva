(() => {
  "use strict";

  const dict = {
    it: {
      title: "Profilo Proprietario",
      sub: "Crea l'account di amministrazione principale per questo nodo.",
      first_label: "Nome del Proprietario",
      last_label: "Cognome (opzionale)",
      err_required: "Inserisci il tuo nome per procedere."
    },
    en: {
      title: "Owner Profile",
      sub: "Set up the primary administrative owner for this node.",
      first_label: "Owner First Name",
      last_label: "Last Name (optional)",
      err_required: "Please enter your name to continue."
    },
    es: {
      title: "Perfil Propietario",
      sub: "Configure la cuenta de administración principal.",
      first_label: "Nombre del Propietario",
      last_label: "Apellido (opcional)",
      err_required: "Por favor ingresa tu nombre para continuar."
    },
    fr: {
      title: "Profil Propriétaire",
      sub: "Configurez le compte d'administration principal.",
      first_label: "Prénom du Propriétaire",
      last_label: "Nom de famille (facultatif)",
      err_required: "Veuillez entrer votre prénom pour continuer."
    }
  };

  window.SetupStepOwnerI18n = { dict };
})();
