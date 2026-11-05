import math
from dataclasses import asdict, dataclass, field

KINDS = ("empty", "guest_only", "authorized", "mixed", "uncertain")
NUCLEUS_ONLY = frozenset({"empty", "guest_only", "uncertain"})
RANK = {"authorized": 3, "mixed": 2, "guest_only": 1, "empty": 0, "uncertain": 0}
MAX_FACES = 32
MAX_VOICES = 64
MAX_VOUCHED = 32


@dataclass(frozen=True)
class Policy:
    stable_ms: int = 1200
    away_ms: int = 10000
    voice_hold_ms: int = 30000
    agree_ms: int = 10000
    continuity_ms: int = 3000
    skew_ms: int = 2000
    face_min: float = 0.5
    voice_min: float = 0.5
    require_liveness: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Reading:
    kind: str
    members: list[dict] = field(default_factory=list)
    guests: int = 0
    unverified: int = 0
    seen: bool = False
    voiced: bool = False


def _number(value) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result


def utterances(voices: list, policy: Policy, now_ms: int) -> dict[str, int]:
    out: dict[str, int] = {}
    for voice in voices[:MAX_VOICES]:
        at = int(voice.get("at_ms") or 0)
        fresh = at <= now_ms + policy.skew_ms and max(0, now_ms - at) < policy.agree_ms
        person = voice.get("person") or ""
        if voice.get("authorized") and person and fresh and _number(voice.get("score")) >= policy.voice_min:
            out[person] = max(out.get(person, 0), min(at, now_ms))
    return out


def recognised(face: dict, policy: Policy) -> str:
    person = face.get("person") or ""
    if not person or not face.get("authorized") or (face.get("liveness") or "unknown") == "spoof":
        return ""
    confidence = _number(face.get("confidence"))
    return "" if math.isnan(confidence) or confidence < policy.face_min else person


def _judge(face: dict, policy: Policy, spoken: set[str], held: frozenset[str]) -> tuple[str, str, str]:
    person = face.get("person") or ""
    liveness = face.get("liveness") or "unknown"
    if not person or not face.get("authorized") or liveness == "spoof":
        return "guest", "", ""
    if not recognised(face, policy):
        return "unverified", "", ""
    live, voiced = liveness == "live", person in spoken
    if live and voiced:
        return "member", person, "strong"
    if not live and not voiced and policy.require_liveness and person not in held:
        return "unverified", "", ""
    return "member", person, "single"


def _classify(members: bool, guests: int, unverified: int) -> str:
    if not members:
        if not guests and not unverified:
            return "empty"
        return "uncertain" if unverified else "guest_only"
    return "mixed" if guests or unverified else "authorized"


def fuse(signals: dict, policy: Policy, now_ms: int, held: frozenset[str] = frozenset()) -> Reading:
    vision = signals.get("vision") or "offline"
    if vision == "disabled":
        return Reading("authorized")
    if vision != "ok":
        return Reading("uncertain")
    faces = list(signals.get("faces") or [])
    spoken = set(utterances(list(signals.get("voices") or []), policy, now_ms))
    members: dict[str, dict] = {}
    guests = unverified = 0
    for face in faces[:MAX_FACES]:
        verdict, person, proof = _judge(face, policy, spoken, held)
        if verdict == "guest":
            guests += 1
        elif verdict == "unverified":
            unverified += 1
        else:
            entry = members.setdefault(person, {"person": person, "proof": proof, "near": False})
            if proof == "strong":
                entry["proof"] = "strong"
            entry["near"] = entry["near"] or bool(face.get("near"))
    for person in spoken:
        members.setdefault(person, {"person": person, "proof": "single", "near": False})
    ordered = [members[k] for k in sorted(members)]
    return Reading(_classify(bool(ordered), guests, unverified), ordered, guests, unverified, bool(faces), bool(spoken))


class Tracker:

    def __init__(self, policy: Policy, now_ms: int) -> None:
        self.policy = policy
        self.current = "uncertain"
        self.since_ms = now_ms
        self.candidate: tuple[str, int] | None = None
        self.last_seen_ms: int | None = None
        self.last_voice_ms: int | None = None
        self.members: list[dict] = []
        self.guests = 0
        self.vouched: dict[str, tuple[int, int]] = {}

    @staticmethod
    def _within(last: int | None, span: int, now_ms: int) -> bool:
        return last is not None and max(0, now_ms - last) < span

    def held(self, now_ms: int) -> frozenset[str]:
        hold, gap = self.policy.voice_hold_ms, self.policy.continuity_ms
        self.vouched = {p: (v, f) for p, (v, f) in self.vouched.items()
                        if max(0, now_ms - v) < hold and max(0, now_ms - f) < gap}
        return frozenset(self.vouched)

    def vouch(self, signals: dict, now_ms: int) -> None:
        if (signals.get("vision") or "offline") != "ok":
            self.vouched.clear()
            return
        voices = utterances(list(signals.get("voices") or []), self.policy, now_ms)
        faces = [f for f in list(signals.get("faces") or [])[:MAX_FACES] if isinstance(f, dict)]
        spoofed = {f.get("person") for f in faces if f.get("liveness") == "spoof"}
        for person in spoofed:
            self.vouched.pop(person, None)
        for person in {recognised(f, self.policy) for f in faces} - spoofed - {""}:
            if person in voices:
                self.vouched[person] = (max(voices[person], self.vouched.get(person, (0, 0))[0]), now_ms)
            elif person in self.vouched:
                self.vouched[person] = (self.vouched[person][0], now_ms)
        if len(self.vouched) > MAX_VOUCHED:
            keep = sorted(self.vouched.items(), key=lambda kv: kv[1], reverse=True)[:MAX_VOUCHED]
            self.vouched = dict(keep)

    def step(self, signals: dict, now_ms: int) -> dict:
        reading = fuse(signals, self.policy, now_ms, self.held(now_ms))
        self.vouch(signals, now_ms)
        if reading.seen:
            self.last_seen_ms = now_ms
        if reading.voiced:
            self.last_voice_ms = now_ms
        self._advance(self._target(reading, now_ms), reading, now_ms)
        return self.audience()

    def _target(self, reading: Reading, now_ms: int) -> str:
        if reading.kind != "empty" or self.current == "empty":
            return reading.kind
        present = self._within(self.last_seen_ms, self.policy.away_ms, now_ms)
        speaking = RANK[self.current] >= RANK["mixed"] and self._within(self.last_voice_ms, self.policy.voice_hold_ms, now_ms)
        return self.current if present or speaking else "empty"

    def _advance(self, target: str, reading: Reading, now_ms: int) -> None:
        if target == self.current:
            self.candidate = None
            if reading.kind == target:
                self._adopt(reading)
            return
        closing = RANK[target] < RANK[self.current] or max(RANK[target], RANK[self.current]) <= 1
        if self.candidate and self.candidate[0] == target:
            stable = max(0, now_ms - self.candidate[1]) >= self.policy.stable_ms
        else:
            self.candidate = (target, now_ms)
            stable = False
        if closing or stable:
            self.current, self.since_ms, self.candidate = target, now_ms, None
            self._adopt(reading)

    def _adopt(self, reading: Reading) -> None:
        self.members = [dict(m) for m in reading.members]
        self.guests = reading.guests

    def audience(self) -> dict:
        return {"kind": self.current, "members": [dict(m) for m in self.members], "guests": self.guests,
                "since_ms": self.since_ms, "nucleus_only": self.current in NUCLEUS_ONLY}
