import re
from typing import List
from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

class KokoroVocalProfile(BaseVocalProfile):
    """
    Profilo 100% indipendente per il motore neurale Kokoro TTS (82M params).
    Motore locale ad altissima fedeltà timbrica e naturalezza prosodica.
    Risponde eccezionalmente a trattini lunghi, virgole e cadenze ritmiche.
    """

    @property
    def engine_id(self) -> str:
        return "kokoro"

    @property
    def display_name(self) -> str:
        return "Kokoro Neural TTS"

    @property
    def supported_tags(self) -> List[str]:
        return []

    def get_system_prompt_instructions(self) -> str:
        return (
            "### GUIDA ESPRESSIVA VOCALE (MOTORE KOKORO NEURALE ATTIVO):\n"
            "Il motore vocale attivo è Kokoro Neurale. Elabora il testo direttamente in fonemi senza markup tra quadre.\n"
            "NON usare tag tra parentesi quadre come [laughs] o [whisper].\n"
            "Sfrutta la straordinaria capacità di intonazione di Kokoro usando la struttura della frase:\n"
            "- Trattini '—' o virgole per pause drammatiche o cambi di pensiero.\n"
            "- Frasi ben ritmate e accenti naturali sulle parole chiave.\n"
            "- Punti esclamativi ben dosati per un tono squillante e accogliente.\n"
            "Esempio: 'Oh, ti ringrazio di cuore — sei davvero una persona squisita! Dimmi, cosa possiamo fare oggi?'\n"
        )

    def prepare_for_synthesis(self, text: str) -> str:
        cleaned = re.sub(r'\[.*?\]', '', text)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip()
