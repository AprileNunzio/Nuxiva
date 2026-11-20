import re
from typing import List
from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

class OpenAITTSVocalProfile(BaseVocalProfile):
    """
    Profilo 100% indipendente per il motore OpenAI TTS (tts-1 / tts-1-hd).
    Il modello interpreta la prosodia attraverso punteggiatura e ritmo contestuale.
    """

    @property
    def engine_id(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI TTS Neural"

    @property
    def supported_tags(self) -> List[str]:
        return []

    def get_system_prompt_instructions(self) -> str:
        return (
            "### GUIDA ESPRESSIVA VOCALE (MOTORE OPENAI TTS ATTIVO):\n"
            "Il motore audio OpenAI interpreta tono ed emozione attraverso la struttura della frase e la punteggiatura.\n"
            "NON inserire tag SSML né parentesi quadre come [laughs] o [pause].\n"
            "Per trasmettere calore, enfasi ed emozione:\n"
            "- Modula le frasi con punteggiatura curata (esclamativi per gioia, puntini per riflessione).\n"
            "- Usa parole descrittive ricche ed espressive.\n"
            "Esempio: 'Ti ringrazio immensamente! Le tue parole sono davvero un raggio di sole oggi.'\n"
        )

    def prepare_for_synthesis(self, text: str) -> str:
        cleaned = re.sub(r'\[.*?\]', '', text)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip()
