import re
from dataclasses import dataclass

_FAST = re.compile(r"mini|flash|haiku|small|nano|lite|fast|instant|8b|3b|1\.5b", re.I)
MAX_PER_SOURCE = 2


@dataclass(frozen=True)
class Preset:
    id: str
    icon: str
    label: str
    hint: str
    scope: str
    sources: tuple[str, ...]


from enum import Enum

class CognitiveEngineVersion(str, Enum):
    LEGACY_4_2 = "nuxiva-4.2-legacy"
    VELOCE_5_0 = "nuxiva-5.0-veloce"
    EMPATICO_5_0 = "nuxiva-5.0-empatico"
    PRO_6_0 = "nuxiva-6.0-pro"
    ULTRA_6_5 = "nuxiva-6.5-ultra"
    AUTO_6_5 = "nuxiva-6.5-auto"

@dataclass(frozen=True)
class ReasoningModeInfo:
    id: str
    name: str
    version: str
    badge: str
    hint: str
    sla_ms: int
    is_default: bool = False


DEFAULT_PRESET_ID = "neuro_core"

PRESETS: tuple[Preset, ...] = (
    Preset(
        "neuro_core",
        "🧠",
        "Nuxiva Neuro-Core 5.0",
        "Piano Corticale Neuro-Biologico e Parallelismo Corticale con dinamica LIF, modulazione limbica e inibizione GABA.",
        "anywhere",
        ("local", "servers", "cloud"),
    ),
    Preset("auto", "✨", "Automatico", "Nuxiva sceglie da sola in base all'hardware.", "anywhere", ()),
    Preset("private", "🔒", "Privato", "Solo modelli in casa: nessun dato esce dalla rete.", "home", ("local", "servers")),
    Preset(
        "balanced",
        "⚖️",
        "Bilanciato",
        "Prima in casa; il cloud solo se la casa non risponde.",
        "home_first",
        ("local", "servers", "cloud"),
    ),
    Preset(
        "smart",
        "🚀",
        "Massima intelligenza",
        "Prima il cloud più capace, la casa come riserva.",
        "anywhere",
        ("cloud", "local", "servers"),
    ),
    Preset("cloud", "☁️", "Solo cloud", "Solo servizi cloud collegati, niente modelli locali.", "anywhere", ("cloud",)),
)
BY_ID = {p.id: p for p in PRESETS}

COGNITIVE_ENGINES: tuple[ReasoningModeInfo, ...] = (
    ReasoningModeInfo(
        id=CognitiveEngineVersion.AUTO_6_5.value,
        name="Nuxiva 6.5 Auto Adattivo",
        version="6.5-auto",
        badge="Auto",
        hint="Meta-Orchestratore Talamico su principio energia libera e carico hardware.",
        sla_ms=45,
        is_default=True,
    ),
    ReasoningModeInfo(
        id=CognitiveEngineVersion.VELOCE_5_0.value,
        name="Nuxiva 5.0 Veloce",
        version="5.0-flash",
        badge="Flash",
        hint="Ternary 1.58-bit con Liquid LNN e risposte sub-25ms per comandi rapidi.",
        sla_ms=25,
        is_default=False,
    ),
    ReasoningModeInfo(
        id=CognitiveEngineVersion.PRO_6_0.value,
        name="Nuxiva 6.0 Pro",
        version="6.0-pro",
        badge="Pro",
        hint="Spazio Latente Continuo JEPA/Coconut con pensiero profondo multi-corsia.",
        sla_ms=1200,
        is_default=False,
    ),
    ReasoningModeInfo(
        id=CognitiveEngineVersion.ULTRA_6_5.value,
        name="Nuxiva 6.5 Ultra",
        version="6.5-ultra",
        badge="Ultra",
        hint="MCTS latente a 64 rami con Process Reward Model dopaminergico.",
        sla_ms=650,
        is_default=False,
    ),
    ReasoningModeInfo(
        id=CognitiveEngineVersion.EMPATICO_5_0.value,
        name="Nuxiva 5.0 Empatico",
        version="5.0-limbic",
        badge="Limbico",
        hint="Global Workspace a 8 corsie parallele con fusione biometrica 10Hz.",
        sla_ms=120,
        is_default=False,
    ),
    ReasoningModeInfo(
        id=CognitiveEngineVersion.LEGACY_4_2.value,
        name="Nuxiva 4.2 Legacy",
        version="4.2-legacy",
        badge="Legacy",
        hint="Pipeline sequenziale a token con fallback seriale di riserva.",
        sla_ms=2500,
        is_default=False,
    ),
)
COGNITIVE_ENGINES_BY_ID = {m.id: m for m in COGNITIVE_ENGINES}

REASONING_MODES: tuple[ReasoningModeInfo, ...] = (
    ReasoningModeInfo(
        id="fast",
        name="Nuxiva 5.0 Veloce",
        version="5.0-flash",
        badge="Veloce",
        hint="Risposta istantanea (<180ms) per conversazione fluida e comandi rapidi.",
        sla_ms=180,
        is_default=False,
    ),
    ReasoningModeInfo(
        id="reasoning",
        name="Nuxiva 5.0 Pro Ragionamento",
        version="5.0-pro",
        badge="Ragionamento",
        hint="Pensiero profondo multi-corsia corticale con validazione critica.",
        sla_ms=1200,
        is_default=True,
    ),
)
REASONING_MODES_BY_ID = {
    **{m.id: m for m in REASONING_MODES},
    **COGNITIVE_ENGINES_BY_ID,
    "nuxiva-5.0-veloce": REASONING_MODES[0],
    "nuxiva-6.0-pro": REASONING_MODES[1],
    "auto": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.AUTO_6_5.value],
    "6.5-auto": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.AUTO_6_5.value],
    "nuxiva-6.5-auto": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.AUTO_6_5.value],
    "fast": REASONING_MODES[0],
    "veloce": REASONING_MODES[0],
    "5.0-flash": REASONING_MODES[0],
    "reasoning": REASONING_MODES[1],
    "pro": REASONING_MODES[1],
    "5.0-pro": REASONING_MODES[1],
    "6.0-pro": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.PRO_6_0.value],
    "ultra": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.ULTRA_6_5.value],
    "6.5-ultra": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.ULTRA_6_5.value],
    "nuxiva-6.5-ultra": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.ULTRA_6_5.value],
    "empatico": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.EMPATICO_5_0.value],
    "empathetic": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.EMPATICO_5_0.value],
    "5.0-limbic": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.EMPATICO_5_0.value],
    "nuxiva-5.0-empatico": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.EMPATICO_5_0.value],
    "legacy": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.LEGACY_4_2.value],
    "4.2-legacy": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.LEGACY_4_2.value],
    "nuxiva-4.2-legacy": COGNITIVE_ENGINES_BY_ID[CognitiveEngineVersion.LEGACY_4_2.value],
}
DEFAULT_REASONING_MODE_ID = CognitiveEngineVersion.AUTO_6_5.value



class PresetError(ValueError):
    pass


def _local(cat: dict, fast: bool) -> list[str]:
    rows = [m for m in cat["local"]["models"] if m["installed"]]
    rows.sort(key=lambda m: m["size_gb"] if m["size_gb"] is not None else 5.0, reverse=not fast)
    return [m["ref"] for m in rows[:MAX_PER_SOURCE]]


def _servers(cat: dict, fast: bool) -> list[str]:
    picks = []
    for server in (s for s in cat["servers"] if s["online"] and s["models"]):
        refs = [m["ref"] for m in server["models"]]
        quick = [r for r in refs if _FAST.search(r)]
        picks.append((quick or refs)[0] if fast else refs[0])
    return picks[:MAX_PER_SOURCE]


def _cloud(cat: dict, fast: bool) -> list[str]:
    picks = []
    for provider in cat["cloud"]:
        refs = [m["ref"] for m in provider["models"]]
        default = next((r for r in refs if r.endswith("/" + provider["default"])), refs[0] if refs else "")
        quick = [r for r in refs if _FAST.search(r.rsplit("/", 1)[-1])]
        choice = (quick[0] if quick else default) if fast else default
        if choice:
            picks.append(choice)
    return picks[:MAX_PER_SOURCE]


def plan(preset_id: str, role_id: str, cat: dict) -> tuple[list[str], str]:
    preset = BY_ID.get(preset_id)
    if not preset:
        raise PresetError("Profilo sconosciuto")
    if preset.id == "auto":
        return [], preset.scope
    fast = role_id == "chat"
    pickers = {"local": _local, "servers": _servers, "cloud": _cloud}
    order = list(dict.fromkeys(ref for source in preset.sources for ref in pickers[source](cat, fast)))
    if not order:
        need = "un servizio cloud collegato" if preset.sources == ("cloud",) else "almeno un modello installato o un server in rete"
        raise PresetError(f"Per il profilo «{preset.label}» serve {need}")
    return order, preset.scope


def clean_profile(value: str | None, custom: bool) -> str:
    if value in BY_ID or value == "custom":
        return value
    return "custom" if custom else DEFAULT_PRESET_ID
