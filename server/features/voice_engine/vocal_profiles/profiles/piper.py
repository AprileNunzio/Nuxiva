import re
from typing import List
from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

class PiperVocalProfile(BaseVocalProfile):
    """
    Profilo 100% indipendente per il motore Piper ONNX Local.
    Ottimizzato per inferenza neurale locale e offline ad altissima velocità.
    NON supporta tag tra parentesi quadre: modula le emozioni tramite punteggiatura e ritmo.
    """

    @property
    def engine_id(self) -> str:
        return "piper"

    @property
    def display_name(self) -> str:
        return "Piper ONNX Local"

    @property
    def supported_tags(self) -> List[str]:
        return []

    def get_system_prompt_instructions(self) -> str:
        return (
            "### GUIDA ESPRESSIVA VOCALE (MOTORE PIPER ONNX LOCALE ATTIVO):\n"
            "Il motore vocale corrente è locale ed offline. NON supporta tag speciali o parentesi quadre.\n"
            "IMPORTANTE: NON inserire MAI espressioni tra parentesi quadre come [laughs], [sighs] o [ride], "
            "perché il sintetizzatore le leggerebbe alla lettera ad alta voce, rovinando l'ascolto!\n"
            "Esprimi calore, emozione e naturalezza esclusivamente tramite punteggiatura espressiva e ritmo:\n"
            "- Usa puntini di sospensione (...) per pause riflessive, sospiri o esitazioni.\n"
            "- Usa punti esclamativi (!) e frasi brevi per entusiasmo, energia e calore.\n"
            "- Usa virgole per cadenzare il respiro e le pause vocali naturali.\n"
            "- Usa interiezioni e risate testuali naturali (es. 'Ah ah!', 'Oh!', 'Eh già!') al posto di tag.\n"
            "Esempio: 'Ma grazie mille!... Davvero, le tue parole mi riempiono di gioia! Fammi sapere come posso aiutarti.'\n"
        )

    def prepare_for_synthesis(self, text: str) -> str:
        # Pulisce rigorosamente qualsiasi parentesi quadra (inclusi tag residui o comandi)
        cleaned = re.sub(r'\[.*?\]', '', text)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip()
