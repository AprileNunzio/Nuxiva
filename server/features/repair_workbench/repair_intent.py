from typing import List

REPAIR_INTENT_ID = "app.nuxiva.repair_workbench"

_TRIGGERS = (
    "banco riparazioni",
    "aggiustare una scheda",
    "riparare una scheda",
    "scheda elettronica",
    "riparazione scheda",
    "repair workbench",
    "repair a board",
)
_ELECTRONICS = (
    "elettronic",
    "pcb",
    "circuito",
    "amplificator",
    "arduino",
    "saldatur",
    "electronic",
)
_AUDIO = ("amplificator", "audio", "hi-fi", "hifi", "preamplificator", "finale")
_FIRMWARE = ("arduino", "esp32", "stm32", "firmware", "microcontroll", "programma")


def _native_router():
    try:
        import nuxiva_native
    except ImportError:
        return None
    factory = getattr(nuxiva_native, "RustIntentRouter", None)
    return factory() if factory is not None else None


def is_repair_request(query: str) -> bool:
    router = _native_router()
    if router is not None and router.resolve_intent(query) == REPAIR_INTENT_ID:
        return True
    lowered = query.lower()
    return any(trigger in lowered for trigger in _TRIGGERS)


def repair_team(lowered_goal: str) -> List[str]:
    if not any(word in lowered_goal for word in _ELECTRONICS):
        return []
    team = ["electronics_repair_engineer", "pcb_schematic_architect"]
    if any(word in lowered_goal for word in _AUDIO):
        team.append("audio_acoustics_specialist")
    if any(word in lowered_goal for word in _FIRMWARE):
        team.append("embedded_firmware_coder")
    return team
