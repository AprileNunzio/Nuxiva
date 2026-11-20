import re
from typing import List
from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

class BarkVocalProfile(BaseVocalProfile):
    """
    Profilo 100% indipendente per il motore generativo Suno Bark TTS.
    Supporta tag inline di suoni non verbali e musicali tra parentesi quadre.
    """

    @property
    def engine_id(self) -> str:
        return "bark"

    @property
    def display_name(self) -> str:
        return "Suno Bark Audio"

    @property
    def supported_tags(self) -> List[str]:
        return ["laughter", "laughs", "sighs", "gasps", "music", "clears throat"]

    def get_system_prompt_instructions(self) -> str:
        return (
            "### GUIDA ESPRESSIVA VOCALE (MOTORE SUNO BARK ATTIVO):\n"
            "Il motore audio Bark supporta tag sonori tra parentesi quadre:\n"
            "- Risata: [laughs] o [laughter]\n"
            "- Sospiri ed emozioni: [sighs], [gasps]\n"
            "- Effetti sonori: [music], [clears throat]\n"
            "- Pause: trattino '—' o '...'\n"
            "Esempio: '[laughs] Ah, che bella sorpresa! [sighs] Mi fa davvero piacere sentirtelo dire.'\n"
        )

    def prepare_for_synthesis(self, text: str) -> str:
        cleaned = re.sub(r'\[reaction:[a-zA-Z0-9_\-]+\]', '', text, flags=re.IGNORECASE)
        return re.sub(r'\s{2,}', ' ', cleaned).strip()
