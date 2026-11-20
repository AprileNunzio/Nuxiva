import re
from typing import List
from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

class ElevenLabsVocalProfile(BaseVocalProfile):
    """
    Profilo 100% indipendente per il motore ElevenLabs Neural Audio.
    Supporta nativamente audio tags inline racchiusi tra parentesi quadre.
    """

    @property
    def engine_id(self) -> str:
        return "elevenlabs"

    @property
    def display_name(self) -> str:
        return "ElevenLabs Neural Audio"

    @property
    def supported_tags(self) -> List[str]:
        return [
            "laughs", "giggles", "chuckles", "snicker",
            "sighs", "gasps", "pant", "pause",
            "whispering", "whisper", "shouting", "softly",
            "clears throat", "groan", "yawn", "cough",
            "crying", "sarcastic"
        ]

    def get_system_prompt_instructions(self) -> str:
        tags_str = ", ".join([f"[{t}]" for t in self.supported_tags])
        return (
            "### GUIDA ESPRESSIVA VOCALE (MOTORE ELEVENLABS ATTIVO):\n"
            "Il motore vocale corrente supporta espressioni vocali e non-verbali inline racchiuse tra parentesi quadre.\n"
            "Arricchisci le tue risposte inserendo questi tag in modo naturale per dare emozione, sfumature umane e ritmo:\n"
            f"- Tag consentiti: {tags_str}\n"
            "- Esempi di utilizzo:\n"
            "  * Ringraziamento / allegria: 'Ti ringrazio tantissimo! [laughs] Sei sempre così gentile.'\n"
            "  * Sorpresa: '[gasps] Davvero è successa una cosa del genere? Incredibile!'\n"
            "  * Riflessione / stanchezza: '[sighs] È stata una giornata intensa, ma abbiamo risolto tutto.'\n"
            "  * Segreto / confidenza: '[whispering] Ti svelo una piccola curiosità...'\n"
            "NON inventare tag non inclusi nella lista. Non inserire tag vuoti o ripetuti senza senso.\n"
        )

    def prepare_for_synthesis(self, text: str) -> str:
        # Rimuove i comandi di reazione visiva [reaction:...] per non sporcare la voce,
        # ma preserva i tag emotivi nativi [laughs], [sighs], ecc.
        cleaned = re.sub(r'\[reaction:[a-zA-Z0-9_\-]+\]', '', text, flags=re.IGNORECASE)
        # Normalizza spazi multipli
        return re.sub(r'\s{2,}', ' ', cleaned).strip()
