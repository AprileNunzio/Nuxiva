from abc import ABC, abstractmethod
from typing import List, Dict, Any
import re

class BaseVocalProfile(ABC):
    """
    Contratto base per ciascun profilo vocale TTS.
    Ogni file di profilo in 'profiles/' è 100% indipendente e definisce
    le regole specifiche del motore (tag ammessi, istruzioni LLM, pulizia e sintesi).
    """

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Identificatore univoco del motore TTS (es. 'elevenlabs', 'piper', 'kokoro', 'azure', 'openai', 'bark')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Nome descrittivo visualizzato per l'utente."""
        pass

    @property
    def supported_tags(self) -> List[str]:
        """Elenco di tutti i tag vocali ammessi da questo motore."""
        return []

    @abstractmethod
    def get_system_prompt_instructions(self) -> str:
        """
        Istruzioni specifiche da iniettare nel System Prompt dell'LLM quando
        questo specifico motore TTS è attivo per l'utente.
        """
        pass

    @abstractmethod
    def prepare_for_synthesis(self, text: str) -> str:
        """
        Pre-elaborazione del testo prima della sintesi audio:
        - Mantiene o adatta i tag supportati nativamente dal motore.
        - Pulisce o rimuove in sicurezza i tag non supportati o comandi UI (es. [reaction:...])
          per evitare che il sintetizzatore legga testo spurio o parentesi quadre.
        """
        pass

    def extract_vocal_tags(self, text: str) -> List[str]:
        """Estrae i tag vocali presenti nel testo."""
        raw_matches = re.findall(r'\[([a-zA-Z_\s]+)\]', text)
        return [m.strip().lower() for m in raw_matches if not m.startswith("reaction:")]

    def to_metadata(self) -> Dict[str, Any]:
        """Serializza le informazioni del profilo per l'interfaccia utente o API."""
        return {
            "engine_id": self.engine_id,
            "display_name": self.display_name,
            "supported_tags": self.supported_tags,
            "has_native_tag_support": len(self.supported_tags) > 0,
        }
