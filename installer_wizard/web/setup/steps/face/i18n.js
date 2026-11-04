(() => {
  "use strict";

  const dict = {
    it: {
      title: "Riconoscimento Facciale Biometrico",
      sub: "Scansione telecamere collegate e mappatura dei punti fisionomici 3D.",
      scanning_cams: "Scansione ingressi video in corso...",
      no_camera: "Nessuna telecamera rilevata sul bus video USB o ONVIF.",
      no_camera_hint: "Puoi procedere senza biometria visiva o collegare una webcam.",
      btn_skip: "Salta Riconoscimento Facciale",
      btn_capture: "Cattura Punti Biometrici",
      shot_front: "1. Guarda dritto al centro",
      shot_left: "2. Ruota il capo a sinistra",
      shot_right: "3. Ruota il capo a destra",
      captured: "Mappatura completata con successo."
    },
    en: {
      title: "Biometric Facial Recognition",
      sub: "Scanning connected cameras and mapping 3D physiognomic landmark points.",
      scanning_cams: "Scanning video inputs...",
      no_camera: "No camera detected on USB video bus or ONVIF network.",
      no_camera_hint: "You can proceed without facial biometrics or plug in a webcam.",
      btn_skip: "Skip Facial Recognition",
      btn_capture: "Capture Biometric Points",
      shot_front: "1. Look straight into camera",
      shot_left: "2. Turn head slightly left",
      shot_right: "3. Turn head slightly right",
      captured: "Landmark mapping completed successfully."
    },
    es: {
      title: "Reconocimiento Facial Biométrico",
      sub: "Escaneo de cámaras y mapeo de puntos fisonómicos 3D.",
      scanning_cams: "Escaneando entradas de video...",
      no_camera: "No se detectó ninguna cámara en el bus USB u ONVIF.",
      no_camera_hint: "Puede continuar sin biometría o conectar una cámara.",
      btn_skip: "Omitir Reconocimiento Facial",
      btn_capture: "Capturar Puntos Biométricos",
      shot_front: "1. Mire recto a la cámara",
      shot_left: "2. Gire la cabeza a la izquierda",
      shot_right: "3. Gire la cabeza a la derecha",
      captured: "Mapeo completado con éxito."
    },
    fr: {
      title: "Reconnaissance Faciale Biométrique",
      sub: "Détection des caméras et cartographie des repères physionomiques 3D.",
      scanning_cams: "Recherche des entrées vidéo en cours...",
      no_camera: "Aucune caméra détectée sur le bus vidéo USB ou ONVIF.",
      no_camera_hint: "Vous pouvez continuer sans biométrie ou brancher une webcam.",
      btn_skip: "Ignorer la Reconnaissance Faciale",
      btn_capture: "Capturer les Points Biométriques",
      shot_front: "1. Regardez droit vers la caméra",
      shot_left: "2. Tournez la tête vers la gauche",
      shot_right: "3. Tournez la tête vers la droite",
      captured: "Cartographie biométrique réussie."
    }
  };

  window.SetupStepFaceI18n = { dict };
})();
