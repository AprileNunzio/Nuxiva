from features.rescue import policy as policy_rules
from features.rescue.fusion import assess, peak, risk
from features.rescue.signals import HAZARDS_OF, MAX_EVIDENCE, expired, validate

MAX_TIMELINE = 128
PERSON = "person"
HYSTERESIS = 0.8
PRIORITY = ("fire", "violence", "intrusion", "medical")
ACTIVE = {"check_in", "alerting", "acknowledged", "emergency"}
TIMED = {"check_in", "alerting", "emergency"}


def tone_of(hazard: str) -> str:
    return "spoken" if hazard in ("medical", "fire") else "discreet"


class Escalation:
    def __init__(self, policy: dict) -> None:
        self.policy = policy
        self.evidence: list[dict] = []
        self.stage = "calm"
        self.hazard: str | None = None
        self.raised: set[str] = set()
        self.deadline = 0.0
        self.tiers = 0
        self.round = 0
        self.explicit = False
        self.cooled: str | None = None
        self.cooldown_until = 0.0
        self.incident = 0
        self.timeline: list[dict] = []

    def observe(self, e: dict, now: float) -> None:
        validate(e, now)
        self.evidence.append(dict(e))
        self._prune(now)

    def _prune(self, now: float) -> None:
        self.evidence = [e for e in self.evidence if not expired(e, now)]
        excess = len(self.evidence) - MAX_EVIDENCE
        if excess > 0:
            self.evidence.sort(key=lambda e: e["at"])
            del self.evidence[:excess]

    def _record(self, at: float, action: dict | None) -> None:
        if len(self.timeline) >= MAX_TIMELINE:
            self.timeline.pop(0)
        self.timeline.append({"at": at, "stage": self.stage, "action": action})

    def _emit(self, out: list, at: float, action: dict) -> None:
        self._record(at, dict(action))
        out.append(action)

    def _at(self, key: str) -> float:
        return policy_rules.scaled(self.policy, key)

    def _open(self, hazard: str) -> None:
        if self.stage not in ACTIVE:
            self.incident += 1
            self.timeline.clear()
            self.raised.clear()
            self.tiers = 0
            self.round = 0
            self.explicit = False
        self.hazard = hazard

    def _check_in(self, hazard: str, wait: float, now: float, out: list) -> None:
        self._open(hazard)
        self.stage = "check_in"
        self.deadline = now + wait
        self._emit(out, now, {"type": "ask_person", "hazard": hazard, "tone": tone_of(hazard)})

    def _raise(self, hazard: str, now: float, out: list) -> None:
        self._open(hazard)
        self.raised.add(hazard)
        if hazard == "fire":
            self._emit(out, now, {"type": "home_alarm", "hazard": hazard})
        if hazard == "medical" and self.stage != "check_in":
            self._emit(out, now, {"type": "ask_person", "hazard": hazard, "tone": "spoken"})
        if self.stage not in ("alerting", "acknowledged", "emergency"):
            self.stage = "alerting"
            self.tiers = 1
            self.deadline = now + self.policy["family_ack_s"]
        self._emit(out, now, {"type": "alert_family", "hazard": hazard, "tier": 0, "tone": tone_of(hazard)})
        self._emit(out, now, {"type": "remind_emergency_number", "hazard": hazard})

    def _urgent(self, hazard: str, value: float) -> bool:
        if hazard == "fire":
            return value >= self._at("check")
        if hazard in ("intrusion", "violence"):
            return value >= self._at("alert")
        return value >= self._at("critical")

    def _cooling(self, hazard: str, now: float) -> bool:
        return self.cooled == hazard and now < self.cooldown_until

    def _start(self, a: dict, now: float, out: list) -> None:
        for hazard in PRIORITY:
            value = risk(a, hazard)
            if self._urgent(hazard, value):
                self._raise(hazard, now, out)
                return
            if self._cooling(hazard, now):
                continue
            if hazard == "medical" and value >= self._at("alert"):
                self._check_in(hazard, self.policy["alert_grace_s"], now, out)
                return
            if hazard != "fire" and value >= self._at("check"):
                self._check_in(hazard, self.policy["check_in_s"], now, out)
                return
        top = peak(a)
        if top >= self._at("watch"):
            if self.stage != "watching":
                self.stage = "watching"
                self._record(now, None)
        elif self.stage == "watching" and top < self._at("watch") * HYSTERESIS:
            self.stage = "calm"
            self._record(now, None)
        elif self.stage == "cooldown" and now >= self.cooldown_until:
            self.stage = "calm"
            self.cooled = None

    def _others(self, a: dict, now: float, out: list) -> None:
        for hazard in PRIORITY:
            if hazard != self.hazard and hazard not in self.raised and self._urgent(hazard, risk(a, hazard)):
                current = self.hazard
                self._raise(hazard, now, out)
                if hazard != "fire":
                    self.hazard = current or hazard

    def _timeouts(self, a: dict, now: float, out: list) -> None:
        hazard = self.hazard
        if hazard is None:
            return
        if self.stage == "check_in":
            value = risk(a, hazard)
            if self._urgent(hazard, value):
                self._raise(hazard, now, out)
            elif now >= self.deadline:
                if value < self._at("watch") and not self.explicit:
                    self._stand_down(now, out)
                else:
                    self._raise(hazard, now, out)
        elif self.stage == "alerting" and now >= self.deadline:
            if self.tiers < self.policy["family_tiers"]:
                tier = self.tiers
                self.tiers += 1
                self.deadline = now + self.policy["family_ack_s"]
                self._emit(out, now, {"type": "alert_family", "hazard": hazard, "tier": tier, "tone": tone_of(hazard)})
            else:
                self.stage = "emergency"
                self.round = 1
                self.deadline = now + self.policy["emergency_repeat_s"]
                self._emit(out, now, {"type": "alert_emergency_contacts", "hazard": hazard, "round": 1})
                self._emit(out, now, {"type": "remind_emergency_number", "hazard": hazard})
        elif self.stage == "emergency" and now >= self.deadline and self.round < self.policy["emergency_rounds"]:
            self.round += 1
            self.deadline = now + self.policy["emergency_repeat_s"]
            self._emit(out, now, {"type": "alert_emergency_contacts", "hazard": hazard, "round": self.round})

    def _stand_down(self, now: float, out: list) -> None:
        hazard = self.hazard
        if hazard is None:
            return
        notified, emergency = self.tiers, self.round > 0
        self.stage = "cooldown"
        self.cooled = hazard
        self.cooldown_until = now + self.policy["cooldown_s"]
        self._emit(out, now, {"type": "stand_down", "hazard": hazard, "notified_tiers": notified, "emergency": emergency})
        self.hazard = None
        self.raised.clear()
        self.tiers = 0
        self.round = 0
        self.explicit = False

    def _step(self, now: float, actions: list, assessment: dict) -> dict:
        return {"at": now, "stage": self.stage, "hazard": self.hazard, "incident": self.incident,
                "deadline": self.deadline if self.stage in TIMED else None, "actions": actions, "assessment": assessment}

    def update(self, now: float) -> dict:
        self._prune(now)
        a = assess(self.evidence, self.policy, now)
        out: list = []
        if self.stage in ACTIVE:
            self._others(a, now, out)
            self._timeouts(a, now, out)
        else:
            self._start(a, now, out)
        return self._step(now, out, a)

    def person_ok(self, now: float) -> dict:
        self.evidence = [e for e in self.evidence if HAZARDS_OF[e["kind"]][0] != "medical" or e["at"] > now]
        self.evidence.append({"kind": "all_clear", "probability": 0.95, "confidence": 1.0, "source": PERSON,
                              "room": None, "at": now})
        out: list = []
        if self.stage in ACTIVE and self.hazard in ("medical", "violence"):
            self._stand_down(now, out)
        return self._step(now, out, assess(self.evidence, self.policy, now))

    def need_help(self, now: float) -> dict:
        out: list = []
        hazard = self.hazard or "medical"
        if self.stage == "alerting":
            self.deadline = now
            self.explicit = True
            self._timeouts(assess(self.evidence, self.policy, now), now, out)
        elif self.stage in ("emergency", "acknowledged"):
            self.explicit = True
            self._emit(out, now, {"type": "remind_emergency_number", "hazard": hazard})
        else:
            self._raise(hazard, now, out)
            self.explicit = True
        return self._step(now, out, assess(self.evidence, self.policy, now))

    def acknowledge(self, tier: int, now: float) -> dict:
        out: list = []
        if self.stage in ("alerting", "emergency"):
            self.stage = "acknowledged"
            self._emit(out, now, {"type": "acknowledged", "tier": tier})
        return self._step(now, out, assess(self.evidence, self.policy, now))

    def dismiss(self, now: float) -> dict:
        out: list = []
        hazard = self.hazard
        if hazard is not None:
            self.evidence = [e for e in self.evidence if hazard not in HAZARDS_OF[e["kind"]] or e["at"] > now]
            if self.stage in ACTIVE:
                self._stand_down(now, out)
        return self._step(now, out, assess(self.evidence, self.policy, now))
