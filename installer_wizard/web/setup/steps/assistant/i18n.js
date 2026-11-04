(() => {
  "use strict";

  const dict = {
    it: {
      title: "Personalizzazione Assistente",
      sub: "Definisci il nome, la personalità vocale e calibra l'attivazione vocale.",
      name_label: "Nome Assistente:",
      voice_label: "Personalità Vocale:",
      voice_female_title: "Voce Femminile",
      voice_female_sub: "Tono caldo ed empatico, modello neurale HD",
      voice_male_title: "Voce Maschile",
      voice_male_sub: "Tono autorevole e chiaro, modello neurale HD",
      voice_neutral_title: "Voce Sintetica",
      voice_neutral_sub: "Tono futuristico cybernetico a bassa latenza",
      wake_title: "Calibrazione Wake-Word (3 Campioni)",
      wake_sub: "Pronuncia il nome dell'assistente per 3 volte per perfezionare l'attivazione a voce.",
      btn_record: "Registra",
      btn_recording: "Ascolto in corso...",
      btn_recorded: "✓ Calibrato"
    },
    en: {
      title: "Assistant Personalization",
      sub: "Define name, vocal persona and calibrate hands-free wake-word detection.",
      name_label: "Assistant Name:",
      voice_label: "Vocal Persona:",
      voice_female_title: "Female Voice",
      voice_female_sub: "Warm and empathetic tone, neural HD model",
      voice_male_title: "Male Voice",
      voice_male_sub: "Clear and authoritative tone, neural HD model",
      voice_neutral_title: "Synthetic Voice",
      voice_neutral_sub: "Futuristic cybernetic tone with ultra-low latency",
      wake_title: "Wake-Word Calibration (3 Samples)",
      wake_sub: "Say the assistant's name 3 times to train the local listening model.",
      btn_record: "Record",
      btn_recording: "Listening...",
      btn_recorded: "✓ Calibrated"
    },
    es: {
      title: "Personalización del Asistente",
      sub: "Defina el nombre, la voz y calibre la activación por voz.",
      name_label: "Nombre del Asistente:",
      voice_label: "Personalidad Vocal:",
      voice_female_title: "Voz Femenina",
      voice_female_sub: "Tono cálido y empático, modelo neuronal HD",
      voice_male_title: "Voz Masculina",
      voice_male_sub: "Tono claro y autoritario, modelo neuronal HD",
      voice_neutral_title: "Voz Sintética",
      voice_neutral_sub: "Tono cibernético futurista de baja latencia",
      wake_title: "Calibración Wake-Word (3 Muestras)",
      wake_sub: "Pronuncie el nombre del asistente 3 veces para entrenar el modelo.",
      btn_record: "Grabar",
      btn_recording: "Escuchando...",
      btn_recorded: "✓ Calibrado"
    },
    fr: {
      title: "Personnalisation de l'Assistant",
      sub: "Définissez le nom, la voix et calibrez l'activation vocale mains libres.",
      name_label: "Nom de l'Assistant :",
      voice_label: "Personnalité Vocale :",
      voice_female_title: "Voix Féminine",
      voice_female_sub: "Ton chaleureux et empathique, modèle neuronal HD",
      voice_male_title: "Voix Masculine",
      voice_male_sub: "Ton clair et autoritaire, modèle neuronal HD",
      voice_neutral_title: "Voix Synthétique",
      voice_neutral_sub: "Ton cybernétique futuriste à très faible latence",
      wake_title: "Calibration Wake-Word (3 Échantillons)",
      wake_sub: "Prononcez le nom de l'assistant 3 fois pour entraîner le modèle.",
      btn_record: "Enregistrer",
      btn_recording: "Écoute en cours...",
      btn_recorded: "✓ Calibré"
    }
  };

  window.SetupStepAssistantI18n = { dict };
})();
