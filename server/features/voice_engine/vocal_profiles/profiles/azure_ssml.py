import re
from typing import List
from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

class AzureSSMLVocalProfile(BaseVocalProfile):
    """
    Profilo 100% indipendente per il motore Microsoft Azure / Edge Neural Speech.
    Supporta lo standard W3C SSML con estensioni neurali mstts per stili ed emozioni.
    """

    @property
    def engine_id(self) -> str:
        return "azure"

    @property
    def display_name(self) -> str:
        return "Microsoft Azure Neural (SSML)"

    @property
    def supported_tags(self) -> List[str]:
        return [
            "cheerful", "empathetic", "excited", "friendly",
            "gentle", "hopeful", "sad", "whispering", "chat"
        ]

    def get_system_prompt_instructions(self) -> str:
        return (
            "### GUIDA ESPRESSIVA VOCALE (MOTORE AZURE SSML ATTIVO):\n"
            "Il motore vocale supporta tag di stile espressivo e pause SSML.\n"
            "Puoi avvolgere frasi o parti del testo con tag di stile, ad esempio:\n"
            "- Stile allegro: <style:cheerful>testo felice</style:cheerful>\n"
            "- Stile empatico: <style:empathetic>comprendo perfettamente</style:empathetic>\n"
            "- Stile bisbigliato: <style:whispering>ti dico un segreto</style:whispering>\n"
            "- Stile entusiasta: <style:excited>fantastico risultato!</style:excited>\n"
            "- Pause temporali: <pause:500ms/> oppure <pause:1s/>\n"
            "Esempio: '<style:cheerful>Che meraviglia sentirti!</style:cheerful> <pause:300ms/> Grazie di cuore per le belle parole!'\n"
            "NON usare parentesi quadre come [laughs].\n"
        )

    def prepare_for_synthesis(self, text: str) -> str:
        # Pulisce comandi di reazione visiva [reaction:...] e tag residui
        cleaned = re.sub(r'\[.*?\]', '', text)
        
        # Converte le abbreviazioni amichevoli in SSML valido se necessario
        cleaned = re.sub(
            r'<style:([a-zA-Z_\-]+)>(.*?)</style:\1>',
            r'<mstts:express-as style="\1">\2</mstts:express-as>',
            cleaned,
            flags=re.DOTALL
        )
        cleaned = re.sub(r'<pause:([0-9a-zA-Z]+)/>', r'<break time="\1"/>', cleaned)
        return cleaned.strip()
