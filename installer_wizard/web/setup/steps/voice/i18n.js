(() => {
  "use strict";

  const dict = {
    it: {
      title: "Riconoscimento Vocale",
      sub: "Calibrazione audio e sensibilità microfono.",
      btn_req_perm: "Attiva Microfono (Richiedi Permesso Browser)",
      sel_mic: "Ingresso Microfonico:",
      test_live: "Livello Ingresso (VU-Meter):",
      param_sample_rate: "Campionamento:",
      param_noise_floor: "Rumore Fondo:",
      param_snr: "SNR Stimato:",
      param_clipping: "Clipping:",
      slider_gain: "Sensibilità / Guadagno:",
      opt_aec: "Cancellazione Eco (AEC)",
      opt_noise: "Soppressione Rumore (NS)"
    },
    en: {
      title: "Voice Recognition",
      sub: "Audio calibration and microphone sensitivity.",
      btn_req_perm: "Activate Microphone (Request Browser Permission)",
      sel_mic: "Microphone Input:",
      test_live: "Input Level (VU-Meter):",
      param_sample_rate: "Sample Rate:",
      param_noise_floor: "Noise Floor:",
      param_snr: "Estimated SNR:",
      param_clipping: "Clipping:",
      slider_gain: "Gain / Sensitivity:",
      opt_aec: "Echo Cancellation (AEC)",
      opt_noise: "Noise Suppression (NS)"
    },
    es: {
      title: "Reconocimiento de Voz",
      sub: "Calibración de audio y sensibilidad del micrófono.",
      btn_req_perm: "Activar Micrófono (Solicitar Permiso del Navegador)",
      sel_mic: "Entrada de Micrófono:",
      test_live: "Nivel de Entrada (VU-Meter):",
      param_sample_rate: "Muestreo:",
      param_noise_floor: "Ruido de Fondo:",
      param_snr: "SNR Estimado:",
      param_clipping: "Saturación:",
      slider_gain: "Ganancia:",
      opt_aec: "Cancelación de Eco (AEC)",
      opt_noise: "Supresión de Ruido (NS)"
    },
    fr: {
      title: "Reconnaissance Vocale",
      sub: "Calibrage audio et sensibilité du microphone.",
      btn_req_perm: "Activer le Microphone (Autoriser le Navigateur)",
      sel_mic: "Entrée Microphone :",
      test_live: "Niveau d'Entrée (VU-mètre) :",
      param_sample_rate: "Échantillonnage :",
      param_noise_floor: "Bruit de Fond :",
      param_snr: "SNR Estimé :",
      param_clipping: "Écrêtage :",
      slider_gain: "Gain / Sensibilité :",
      opt_aec: "Annulation d'Écho (AEC)",
      opt_noise: "Suppression du Bruit (NS)"
    }
  };

  window.SetupStepVoiceI18n = { dict };
})();
