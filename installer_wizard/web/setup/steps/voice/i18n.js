(() => {
  "use strict";

  const dict = {
    it: {
      title: "Riconoscimento Vocale & Microfoni",
      sub: "Calibrazione della cattura audio, analisi dello spettro acustico e sensibilità.",
      sel_mic: "Dispositivo di Ingresso Microfonico:",
      test_live: "Livello di Ingresso in Tempo Reale (VU-Meter):",
      param_sample_rate: "Campionamento:",
      param_noise_floor: "Rumore Fondo:",
      param_snr: "SNR Stimato:",
      param_clipping: "Clipping:",
      slider_gain: "Sensibilità / Guadagno Software:",
      opt_aec: "Cancellazione Acustica dell'Eco (AEC)",
      opt_noise: "Soppressione Neurale del Rumore (NS)"
    },
    en: {
      title: "Voice Recognition & Microphones",
      sub: "Audio capture calibration, acoustic spectrum analysis and sensitivity.",
      sel_mic: "Microphone Input Device:",
      test_live: "Real-time Input Level (VU-Meter):",
      param_sample_rate: "Sample Rate:",
      param_noise_floor: "Noise Floor:",
      param_snr: "Estimated SNR:",
      param_clipping: "Clipping:",
      slider_gain: "Software Gain / Sensitivity:",
      opt_aec: "Acoustic Echo Cancellation (AEC)",
      opt_noise: "Neural Noise Suppression (NS)"
    },
    es: {
      title: "Reconocimiento de Voz y Micrófonos",
      sub: "Calibración de captura de audio, análisis acústico y sensibilidad.",
      sel_mic: "Dispositivo de Entrada de Micrófono:",
      test_live: "Nivel de Entrada en Tiempo Real (VU-Meter):",
      param_sample_rate: "Muestreo:",
      param_noise_floor: "Ruido de Fondo:",
      param_snr: "SNR Estimado:",
      param_clipping: "Saturación:",
      slider_gain: "Sensibilidad / Ganancia:",
      opt_aec: "Cancelación de Eco Acústico (AEC)",
      opt_noise: "Supresión Neuronal de Ruido (NS)"
    },
    fr: {
      title: "Reconnaissance Vocale & Microphones",
      sub: "Calibrage de la capture audio, analyse spectrale et sensibilité.",
      sel_mic: "Périphérique d'Entrée Micro:",
      test_live: "Niveau d'Entrée en Temps Réel (VU-mètre):",
      param_sample_rate: "Échantillonnage:",
      param_noise_floor: "Bruit de Fond:",
      param_snr: "SNR Estimé:",
      param_clipping: "Écrêtage:",
      slider_gain: "Sensibilité / Gain Logiciel:",
      opt_aec: "Annulation d'Écho Acoustique (AEC)",
      opt_noise: "Suppression Neuronale du Bruit (NS)"
    }
  };

  window.SetupStepVoiceI18n = { dict };
})();
