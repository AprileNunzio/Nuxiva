import importlib
import inspect
import logging
import os
import pkgutil
from typing import Dict, List, Optional

from server.features.voice_engine.vocal_profiles.contracts import BaseVocalProfile

logger = logging.getLogger("nuxiva.voice_engine.registry")

class VocalProfileRegistry:
    """
    Registro dinamico dei profili vocali TTS.
    Scansiona automaticamente la directory 'profiles/' caricando
    ogni file indipendente senza richiedere modifiche al codice centrale.
    """

    def __init__(self):
        self._profiles: Dict[str, BaseVocalProfile] = {}
        self._discover_and_register_profiles()

    def _discover_and_register_profiles(self) -> None:
        from server.features.voice_engine.vocal_profiles import profiles as profiles_pkg

        package_path = os.path.dirname(profiles_pkg.__file__)
        prefix = f"{profiles_pkg.__name__}."

        for _, module_name, is_pkg in pkgutil.iter_modules([package_path], prefix):
            if is_pkg:
                continue
            try:
                mod = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, BaseVocalProfile) and obj is not BaseVocalProfile:
                        instance = obj()
                        self.register_profile(instance)
            except Exception as exc:
                logger.warning("Impossibile caricare profilo vocale da %s: %s", module_name, exc)

    def register_profile(self, profile: BaseVocalProfile) -> None:
        """Registra un nuovo profilo vocale."""
        self._profiles[profile.engine_id.lower()] = profile
        logger.debug("Registrato profilo vocale TTS: %s (%s)", profile.engine_id, profile.display_name)

    def get_profile(self, engine_id: Optional[str] = None) -> BaseVocalProfile:
        """
        Restituisce il profilo associato a engine_id.
        Se non specificato o sconosciuto, usa 'elevenlabs' o 'piper' come fallback.
        """
        normalized = (engine_id or "elevenlabs").lower().strip()
        if normalized in self._profiles:
            return self._profiles[normalized]
        
        # Fallback intelligenti
        if "piper" in self._profiles:
            return self._profiles["piper"]
        if "elevenlabs" in self._profiles:
            return self._profiles["elevenlabs"]
        
        # In caso estremo, restituisce il primo disponibile
        return next(iter(self._profiles.values()))

    def list_profiles(self) -> List[Dict[str, any]]:
        """Restituisce l'elenco dei metadati di tutti i profili registrati."""
        return [profile.to_metadata() for profile in self._profiles.values()]


vocal_profile_registry = VocalProfileRegistry()
