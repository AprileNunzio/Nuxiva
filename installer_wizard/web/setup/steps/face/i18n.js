(() => {
  "use strict";

  const dict = {
    it: {
      title: "Riconoscimento Facciale",
      sub: "Mappatura fisionomica 3D e verifica telecamere.",
      btn_req_perm: "Attiva Webcam (Richiedi Permesso Browser)",
      perm_denied: "Permesso webcam non concesso nel browser.",
      scanning_cams: "Scansione ingressi video...",
      no_camera: "Nessuna telecamera rilevata.",
      no_camera_hint: "Puoi procedere senza biometria facciale o collegare una webcam.",
      btn_skip: "Salta Riconoscimento Facciale",
      btn_capture: "Cattura Punti Biometrici",
      shot_front: "1. Guarda dritto al centro",
      shot_left: "2. Ruota il capo a sinistra",
      shot_right: "3. Ruota il capo a destra",
      captured: "Mappatura completata con successo."
    },
    en: {
      title: "Facial Recognition",
      sub: "3D physiognomic mapping and camera verification.",
      btn_req_perm: "Activate Webcam (Request Browser Permission)",
      perm_denied: "Webcam permission was not granted in browser.",
      scanning_cams: "Scanning video inputs...",
      no_camera: "No camera detected.",
      no_camera_hint: "You can proceed without facial biometrics or connect a webcam.",
      btn_skip: "Skip Facial Recognition",
      btn_capture: "Capture Biometric Points",
      shot_front: "1. Look straight into camera",
      shot_left: "2. Turn head slightly left",
      shot_right: "3. Turn head slightly right",
      captured: "Mapping completed successfully."
    },
    es: {
      title: "Reconocimiento Facial",
      sub: "Mapeo fisonómico 3D y verificación de cámaras.",
      btn_req_perm: "Activar Cámara (Solicitar Permiso del Navegador)",
      perm_denied: "Permiso de cámara no concedido en el navegador.",
      scanning_cams: "Escaneando entradas de video...",
      no_camera: "No se detectó ninguna cámara.",
      no_camera_hint: "Puede continuar sin biometría o conectar una cámara.",
      btn_skip: "Omitir Reconocimiento Facial",
      btn_capture: "Capturar Puntos Biométricos",
      shot_front: "1. Mire recto a la cámara",
      shot_left: "2. Gire la cabeza a la izquierda",
      shot_right: "3. Gire la cabeza a la derecha",
      captured: "Mapeo completado con éxito."
    },
    fr: {
      title: "Reconnaissance Faciale",
      sub: "Cartographie physionomique 3D et détection caméra.",
      btn_req_perm: "Activer la Caméra (Autoriser le Navigateur)",
      perm_denied: "Autorisation caméra refusée dans le navigateur.",
      scanning_cams: "Recherche des caméras...",
      no_camera: "Aucune caméra détectée.",
      no_camera_hint: "Vous pouvez continuer sans biométrie ou brancher une webcam.",
      btn_skip: "Ignorer la Reconnaissance Faciale",
      btn_capture: "Capturer les Points Biométriques",
      shot_front: "1. Regardez droit vers la caméra",
      shot_left: "2. Tournez la tête vers la gauche",
      shot_right: "3. Tournez la tête vers la droite",
      captured: "Cartographie réussie."
    }
  };

  window.SetupStepFaceI18n = { dict };
})();
