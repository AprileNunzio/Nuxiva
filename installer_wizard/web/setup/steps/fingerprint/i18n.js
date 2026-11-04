(() => {
  "use strict";

  const dict = {
    it: {
      title: "Riconoscimento Impronta Digitale",
      sub: "Registrazione biometrica per autenticazione istantanea senza password.",
      scan_prompt: "Tocca il sensore con il polpastrello",
      touch_1: "Tocco 1: Centro del dito",
      touch_2: "Tocco 2: Bordo sinistro",
      touch_3: "Tocco 3: Bordo destro",
      success_badge: "Impronta digitale registrata con successo.",
      no_sensor: "Nessun sensore biometrico d'impronte rilevato.",
      no_sensor_sub: "Questo dispositivo non dispone di un lettore hardware compatibile. Puoi procedere regolarmente."
    },
    en: {
      title: "Fingerprint Recognition",
      sub: "Biometric enrollment for instant passwordless authentication.",
      scan_prompt: "Touch the sensor with your fingertip",
      touch_1: "Touch 1: Center of finger",
      touch_2: "Touch 2: Left edge",
      touch_3: "Touch 3: Right edge",
      success_badge: "Fingerprint enrolled successfully.",
      no_sensor: "No fingerprint sensor detected on hardware.",
      no_sensor_sub: "This machine lacks a compatible fingerprint reader. You can proceed normally."
    },
    es: {
      title: "Reconocimiento de Huella Digital",
      sub: "Registro biométrico para autenticación instantánea sin contraseña.",
      scan_prompt: "Toque el sensor con la yema del dedo",
      touch_1: "Toque 1: Centro del dedo",
      touch_2: "Toque 2: Borde izquierdo",
      touch_3: "Toque 3: Borde derecho",
      success_badge: "Huella dactilar registrada con éxito.",
      no_sensor: "No se detectó ningún lector de huellas dactilares.",
      no_sensor_sub: "Este dispositivo no dispone de lector compatible. Puede continuar con normalidad."
    },
    fr: {
      title: "Reconnaissance d'Empreinte Digitale",
      sub: "Enrôlement biométrique pour une authentification instantanée sans mot de passe.",
      scan_prompt: "Posez votre doigt sur le capteur",
      touch_1: "Toucher 1 : Centre du doigt",
      touch_2: "Toucher 2 : Bord gauche",
      touch_3: "Toucher 3 : Bord droit",
      success_badge: "Empreinte digitale enregistrée avec succès.",
      no_sensor: "Aucun lecteur d'empreintes détecté.",
      no_sensor_sub: "Cet appareil ne dispose pas d'un capteur compatible. Vous pouvez continuer normalement."
    }
  };

  window.SetupStepFingerprintI18n = { dict };
})();
