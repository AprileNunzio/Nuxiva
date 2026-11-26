import json
import time
from dataclasses import dataclass, field

from agenti.reasoning import models, sources, state

ROLES = {"owner": "owner", "family": "family", "staff": "staff", "child": "child", "guest": "guest", "system": "owner"}


@dataclass
class Thought:
    raw_goal: str = ""
    goal: dict = field(default_factory=dict)
    checked: dict | None = None
    code: str = ""
    stage: str = "understand"
    tokens: int = 0
    corrections: int = 0
    started: float = field(default_factory=time.monotonic)

    @property
    def latency_ms(self) -> int:
        return int((time.monotonic() - self.started) * 1000)

    @property
    def valid(self) -> bool:
        return self.checked is not None

    @property
    def executable(self) -> bool:
        return bool(self.checked and self.checked.get("executable"))

    @property
    def capabilities(self) -> list[str]:
        return list(self.checked.get("capabilities", [])) if self.checked else []

    def public(self) -> dict:
        return {"intent": self.goal.get("intent", ""), "language": self.goal.get("language", ""), "risk": self.goal.get("risk", ""),
                "stage": self.stage, "code": self.code, "capabilities": self.capabilities,
                "missing": (self.checked or {}).get("missing", []), "approvals": (self.checked or {}).get("approvals", []),
                "cached": bool((self.checked or {}).get("cached")), "tokens": self.tokens, "corrections": self.corrections,
                "latency_ms": self.latency_ms}


def role_of(name: str) -> str:
    return ROLES.get(name, "guest")


def _threshold(engine) -> int:
    return int(json.loads(engine.config())["understand_threshold_bps"])


async def think(text: str, role: str, external: str | None = None, privacy: str = "") -> Thought:
    engine = state.engine()
    sources.sync()
    thought = Thought()
    request = json.loads(engine.understand_request(text, external))
    thought.raw_goal, spent = await models.understand(request, privacy)
    thought.tokens += spent
    try:
        thought.goal = json.loads(engine.goal(thought.raw_goal, text))
    except ValueError as exc:
        thought.code = str(exc)
        return thought
    if thought.goal.get("confidence_bps", 0) < _threshold(engine):
        thought.code = "reason.goal.low_confidence"
        return thought
    thought.stage = "plan"
    prepared = json.loads(engine.prepare(thought.raw_goal, text, role, state.now_ms()))
    if prepared["kind"] == "cached":
        thought.checked = prepared["checked"]
        return thought
    plan_request = prepared["request"]
    while True:
        raw_plan, spent = await models.plan(plan_request, privacy)
        thought.tokens += spent
        verdict = json.loads(engine.accept(thought.raw_goal, text, role, raw_plan, json.dumps(plan_request["capabilities"]),
                                           thought.corrections, state.now_ms()))
        if verdict["kind"] == "accepted":
            thought.checked = verdict["checked"]
            return thought
        thought.code = verdict["code"]
        if verdict["kind"] == "rejected":
            return thought
        thought.corrections += 1
        plan_request = verdict["request"]
