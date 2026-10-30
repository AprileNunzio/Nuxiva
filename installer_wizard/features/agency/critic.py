from dataclasses import asdict, dataclass, field

from features.agency import prompts
from features.agency.blueprint import Blueprint, extend
from features.agency.text import clean, estimate_tokens, strings
from features.brain import llm

ROUNDS = 2
CRITIQUE_TOKENS = 2500
REVIEW_TOKENS = 900
QUESTIONS = 12


@dataclass
class Exchange:
    question: str
    answer: str


@dataclass
class Reasoning:
    exchanges: list[Exchange] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    approved: bool
    feedback: str
    tokens: int


def _exchanges(raw) -> list[Exchange]:
    out = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            q, a = clean(item.get("q"), 400), clean(item.get("a"), 1200)
            if q and a:
                out.append(Exchange(q, a))
    return out[:QUESTIONS]


async def interrogate(goal: str, blueprint: Blueprint, language_name: str) -> tuple[Reasoning, int]:
    reasoning, tokens = Reasoning(), 0
    for _ in range(ROUNDS):
        prompt = prompts.critique(goal, blueprint.to_dict(), language_name)
        raw = await llm.generate(prompt, as_json=True, max_tokens=CRITIQUE_TOKENS, temperature=0.2,
                                 system=prompts.CRITIC, component="agency_critic")
        tokens += estimate_tokens(prompt, str(raw))
        data = raw if isinstance(raw, dict) else {}
        reasoning.exchanges.extend(_exchanges(data.get("questions")))
        reasoning.issues.extend(strings(data.get("issues"), 500, 12))
        added = extend(blueprint, data.get("missing_tasks"))
        reasoning.added.extend(t.id for t in added)
        if str(data.get("verdict", "ok")).lower() != "revise" or not added:
            break
    return reasoning, tokens


async def review(task: dict, delivered: str, language_name: str) -> Verdict:
    prompt = prompts.review(task, delivered, language_name)
    raw = await llm.generate(prompt, as_json=True, max_tokens=REVIEW_TOKENS, temperature=0.1,
                             system=prompts.REVIEWER, component="agency_critic")
    data = raw if isinstance(raw, dict) else {}
    feedback = clean(data.get("feedback"), 3000)
    approved = str(data.get("verdict", "")).lower() == "approve" and bool(delivered.strip())
    return Verdict(approved, feedback, estimate_tokens(prompt, str(raw)))
