import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from server.features.llm_gateway.contracts import CognitiveEngineVersion

LANG_DIR = Path(__file__).resolve().parent / "language"
LANGS = ("it", "en", "es", "fr")
FALLBACK = "it"
CHAT_SLA_MS = 50
DEEP_SLA_MS = 1500
PICKS = ("sequential", "first", "best")
CONFIDENCE_WEIGHT = 0.55
CRITIC_WEIGHT = 0.45


def lang_of(lang: Any) -> str:
    code = str(lang or "").lower()[:2]
    return code if code in LANGS else FALLBACK


@lru_cache(maxsize=8)
def _texts(lang: str) -> dict:
    return json.loads((LANG_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def text(section: str, key: str, lang: Any = None) -> Any:
    found = _texts(lang_of(lang)).get(section, {}).get(key)
    return found if found is not None else _texts(FALLBACK)[section][key]


def stage(kind: str, key: str, label: str, lang: Any = None, **params: Any) -> Dict[str, Any]:
    words = text("stages", key, lang)
    return {"kind": kind, "name": words["name"].format(**params), "detail": words["detail"].format(**params), "label": label}


@dataclass(frozen=True)
class Strategy:
    kind: str
    candidates: int
    pick: str
    critic: bool
    wait_s: float

    def __post_init__(self) -> None:
        if self.kind not in ("chat", "deep") or self.pick not in PICKS or not 1 <= self.candidates <= 4 or self.wait_s < 0:
            raise ValueError(f"strategia non valida: {self}")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseReasoningEngine(ABC):
    @property
    @abstractmethod
    def key(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> CognitiveEngineVersion:
        pass

    @property
    @abstractmethod
    def strategy(self) -> Strategy:
        pass

    @property
    def icon(self) -> str:
        return "🧠"

    @property
    def is_default(self) -> bool:
        return False

    def label(self, lang: Any = None) -> str:
        return text("engines", self.key, lang)["name"]

    def summary(self, lang: Any = None) -> str:
        return text("engines", self.key, lang)["summary"]

    @property
    def name(self) -> str:
        return self.label()

    @property
    def architecture(self) -> str:
        return self.summary()

    @property
    def latency_sla_ms(self) -> int:
        return CHAT_SLA_MS if self.strategy.kind == "chat" else DEEP_SLA_MS

    @property
    def vram_mb(self) -> int:
        return 0

    def effective(self, query: str = "", limbic: Any = None) -> "BaseReasoningEngine":
        return self

    def route_stages(self, query: str, limbic: Any, lang: Any) -> List[Dict[str, Any]]:
        return []

    def get_flow_stages(self, query: str = "", context: Optional[Dict[str, Any]] = None, limbic: Any = None,
                        candidates: Optional[int] = None) -> List[Dict[str, Any]]:
        lang = (context or {}).get("ui_lang")
        chosen = self.effective(query, limbic)
        plan = chosen.strategy
        count = min(plan.candidates, candidates) if candidates else plan.candidates
        out = list(self.route_stages(query, limbic, lang))
        if plan.pick == "sequential":
            out.append(stage("reasoning", "sequential", "sequential", lang, count=count))
        elif plan.pick == "first":
            out.append(stage("reasoning", "first", "race", lang, count=count))
        else:
            out.append(stage("reasoning", "best", "compare", lang, count=count, wait=f"{plan.wait_s:g}"))
        if plan.critic:
            out.append(stage("critic", "critic", "critic", lang, cw=CONFIDENCE_WEIGHT, kw=CRITIC_WEIGHT))
        out.append(stage("decision", "decision", "decision", lang))
        return out

    def get_profile(self, is_active: bool = False, lang: Any = None) -> Dict[str, Any]:
        ver_str = getattr(self.version, "value", str(self.version))
        badge = ver_str.removeprefix("nuxiva-")
        return {
            "id": ver_str,
            "version": badge,
            "badge": badge,
            "name": self.label(lang),
            "architecture": self.summary(lang),
            "hint": self.summary(lang),
            "strategy": self.strategy.as_dict(),
            "latency_sla_ms": self.latency_sla_ms,
            "sla_ms": self.latency_sla_ms,
            "vram_mb": self.vram_mb,
            "icon": self.icon,
            "is_default": self.is_default,
            "active": is_active,
        }
