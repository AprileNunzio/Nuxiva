import datetime
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("nuxiva.reflex_bridge")

try:
    from nuxiva_native import RustReflexEngine
    _HAS_NATIVE_REFLEX = True
except ImportError:
    _HAS_NATIVE_REFLEX = False
    RustReflexEngine = None


class PythonReflexFallback:
    """Fallback gemello in Python qualora il modulo nativo binario sia in fase di build."""
    def __init__(self) -> None:
        self._learned = {}

    def evaluate(
        self,
        query: str,
        *,
        vocal_energy_rms: float = 0.15,
        pitch_hz: float = 140.0,
        hour_of_day: int = 14,
    ) -> Dict[str, Any]:
        is_whisper = 0.001 < vocal_energy_rms < 0.040
        is_night = hour_of_day >= 22 or hour_of_day < 7

        if is_whisper:
            delivery_style = "whisper"
            volume_scale = 0.35
        elif is_night:
            delivery_style = "night_discreet"
            volume_scale = 0.55
        else:
            delivery_style = "normal"
            volume_scale = 1.0

        # Language basic heuristic detection
        lower_q = f" {query.lower()} "
        if any(w in lower_q for w in [" spieg", " perche", " perché", " accendi", " spegni", " dei ", " della ", " delle ", " ciao ", " grazie ", " cosa ", " come ", " dimmi "]):
            lang = "it"
        elif any(w in lower_q for w in [" the ", " what ", " please ", " turn ", " light ", " weather ", " explain "]):
            lang = "en"
        elif any(w in lower_q for w in [" por favor ", " enciende ", " apaga ", " explica ", " gracias ", " hola "]):
            lang = "es"
        elif any(w in lower_q for w in [" s'il vous ", " allume ", " eteins ", " explique ", " merci ", " bonjour "]):
            lang = "fr"
        elif any(w in lower_q for w in [" bitte ", " schalte ", " danke ", " hallo ", " erkläre "]):
            lang = "de"
        else:
            lang = "it"

        # Immediate Zero-Silence Fillers
        if delivery_style == "whisper":
            fillers = {
                "en": "One sec...",
                "es": "Un segundo...",
                "fr": "Un instant...",
                "de": "Einen Moment...",
                "it": "Un attimo...",
            }
        elif delivery_style == "night_discreet":
            fillers = {
                "en": "Checking quietly for you...",
                "es": "Lo reviso enseguida...",
                "fr": "Je m'en occupe discrètement...",
                "de": "Ich kümmere mich leise darum...",
                "it": "Controllo subito per te...",
            }
        else:
            fillers = {
                "en": "Working on it right now...",
                "es": "¡Enseguida me pongo con ello!",
                "fr": "Tout de suite, je m'en occupe !",
                "de": "Sofort, ich kümmere mich darum!",
                "it": "Ci penso io, verifico all'istante...",
            }
        immediate_filler = fillers.get(lang, fillers["it"])

        # Plasticity lookup
        learned_entry = self._learned.get(query.strip().lower())
        fast_intent = learned_entry["intent"] if learned_entry else None
        fast_action = learned_entry["action"] if learned_entry else None
        should_fast = bool(learned_entry)

        return {
            "language": lang,
            "is_whisper": is_whisper,
            "is_night": is_night,
            "delivery_style": delivery_style,
            "volume_scale": volume_scale,
            "immediate_filler": immediate_filler,
            "should_execute_fast": should_fast,
            "fast_intent": fast_intent,
            "fast_action": fast_action,
            "fast_confidence": 0.95 if should_fast else 0.0,
            "is_guaranteed": should_fast,
            "latency_us": 450,
        }

    def learn(self, query: str, intent: str, action: str) -> bool:
        self._learned[query.strip().lower()] = {"intent": intent, "action": action}
        return True


class ReflexBridge:
    def __init__(self) -> None:
        if _HAS_NATIVE_REFLEX and RustReflexEngine is not None:
            try:
                self._engine = RustReflexEngine()
                self._is_native = True
                logger.info("ReflexBridge initialized with RustReflexEngine (native)")
            except Exception as e:
                logger.warning("Could not initialize native RustReflexEngine (%s), using fallback", e)
                self._engine = PythonReflexFallback()
                self._is_native = False
        else:
            self._engine = PythonReflexFallback()
            self._is_native = False
            logger.info("ReflexBridge initialized with PythonReflexFallback")

    def evaluate(
        self,
        query: str,
        vocal_energy_rms: float = 0.15,
        pitch_hz: float = 140.0,
        hour_of_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        if hour_of_day is None:
            hour_of_day = datetime.datetime.now().hour

        return self._engine.evaluate(
            query,
            vocal_energy_rms=vocal_energy_rms,
            pitch_hz=pitch_hz,
            hour_of_day=hour_of_day,
        )

    def learn(self, query: str, intent: str, action: str) -> bool:
        return self._engine.learn(query, intent, action)

    @property
    def is_native(self) -> bool:
        return self._is_native


reflex_bridge = ReflexBridge()
