import time

STAGES = ("assessment", "treatment", "consolidation")
PHASES = ("opening", "central", "closing")
WEEK = 7 * 86400
OPENING_MAX = 300.0
OPENING_MIN_TURNS = 3
CENTRAL_SOFT = 30 * 60
CENTRAL_HARD = 35 * 60
ASSESSMENT_SESSIONS = 3
TREATMENT_MIN = 8
TREATMENT_MAX = 12
CONSOLIDATION_BIWEEKLY = 2
CONSOLIDATION_END = 6


def phase_for(started: float, central_at: float | None, user_turns: int, now: float, closing: bool = False) -> str:
    if closing:
        return "closing"
    if central_at is None:
        return "central" if user_turns >= OPENING_MIN_TURNS or now - started >= OPENING_MAX else "opening"
    return "closing" if now - central_at >= CENTRAL_HARD else "central"


def nearing_end(central_at: float | None, now: float) -> bool:
    return central_at is not None and CENTRAL_SOFT <= now - central_at < CENTRAL_HARD


def next_interval(stage: str, in_stage: int) -> int:
    if stage == "consolidation":
        return 2 * WEEK if in_stage < CONSOLIDATION_BIWEEKLY else 30 * 86400
    return WEEK


def advance(stage: str, in_stage: int, improving: bool) -> tuple[str, bool]:
    if stage == "assessment" and in_stage >= ASSESSMENT_SESSIONS:
        return "treatment", False
    if stage == "treatment" and (in_stage >= TREATMENT_MAX or (in_stage >= TREATMENT_MIN and improving)):
        return "consolidation", False
    if stage == "consolidation" and in_stage >= CONSOLIDATION_END:
        return "consolidation", True
    return stage, False


def schedule(stage: str, in_stage: int, ended: float) -> float:
    return ended + next_interval(stage, in_stage)


def due(next_at: float | None, now: float | None = None) -> bool:
    return next_at is not None and (now or time.time()) >= next_at
