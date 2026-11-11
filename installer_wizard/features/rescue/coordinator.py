import json
import logging
import threading
import time

from features.redalert.service import RedAlert
from features.rescue.engine import Rescue
from features.sentinel import record

log = logging.getLogger("nuxiva.rescue.coordinator")


class RescueCoordinator:
    def __init__(self, policy: str = "", prefer_native: bool = True) -> None:
        self.policy_str = policy
        self.prefer_native = prefer_native
        self.rescue = Rescue(policy, prefer_native=prefer_native)
        self.last_step: dict = {}
        self._lock = threading.Lock()

    def observe(self, kind: str, probability: float, confidence: float, source: str,
                at: float | None = None, now: float | None = None, room: str | None = None) -> dict:
        cur_now = float(now if now is not None else time.time())
        cur_at = float(at if at is not None else cur_now)
        with self._lock:
            self.rescue.observe(kind, probability, confidence, source, cur_at, cur_now, room)
            step = self.rescue.update(cur_now)
            self.last_step = step
            self._dispatch_actions(step.get("actions", []), cur_now)
            return step

    def update(self, now: float | None = None) -> dict:
        cur_now = float(now if now is not None else time.time())
        with self._lock:
            step = self.rescue.update(cur_now)
            self.last_step = step
            self._dispatch_actions(step.get("actions", []), cur_now)
            return step

    def person_ok(self, now: float | None = None) -> dict:
        cur_now = float(now if now is not None else time.time())
        with self._lock:
            step = self.rescue.person_ok(cur_now)
            self.last_step = step
            self._dispatch_actions(step.get("actions", []), cur_now)
            try:
                record.record("system.recovered", record.NUXIVA, "sentinel.rescue.person_ok",
                              {}, "sensitive", "rescue", at=cur_now)
            except Exception as exc:
                log.debug("Sentinel person_ok audit error: %s", exc)
            return step

    def need_help(self, now: float | None = None) -> dict:
        cur_now = float(now if now is not None else time.time())
        with self._lock:
            step = self.rescue.need_help(cur_now)
            self.last_step = step
            self._dispatch_actions(step.get("actions", []), cur_now)
            try:
                record.record("system.alert", record.NUXIVA, "sentinel.rescue.need_help",
                              {}, "sensitive", "rescue", at=cur_now)
            except Exception as exc:
                log.debug("Sentinel need_help audit error: %s", exc)
            return step

    def acknowledge(self, tier: int, now: float | None = None) -> dict:
        cur_now = float(now if now is not None else time.time())
        with self._lock:
            step = self.rescue.acknowledge(tier, cur_now)
            self.last_step = step
            self._dispatch_actions(step.get("actions", []), cur_now)
            return step

    def dismiss(self, now: float | None = None) -> dict:
        cur_now = float(now if now is not None else time.time())
        with self._lock:
            step = self.rescue.dismiss(cur_now)
            self.last_step = step
            self._dispatch_actions(step.get("actions", []), cur_now)
            return step

    def status(self) -> dict:
        with self._lock:
            return {
                "stage": self.last_step.get("stage", "calm"),
                "hazard": self.last_step.get("hazard"),
                "deadline": self.last_step.get("deadline"),
                "incident": self.last_step.get("incident", 0),
                "timeline": self.rescue.timeline(),
                "policy": self.rescue.policy(),
                "native": self.rescue.native,
            }

    def set_policy(self, policy: str | dict) -> dict:
        p_str = json.dumps(policy) if isinstance(policy, dict) else str(policy)
        with self._lock:
            self.policy_str = p_str
            self.rescue = Rescue(p_str, prefer_native=self.prefer_native)
            self.last_step = {}
            return self.rescue.policy()

    def _dispatch_actions(self, actions: list[dict], now: float) -> None:
        for a in actions:
            act_type = a.get("type")
            hazard = str(a.get("hazard") or "medical")
            if act_type == "ask_person":
                try:
                    record.record("system.alert", record.NUXIVA, "sentinel.rescue.alert",
                                  {"hazard": hazard, "source": "rescue", "confidence": "90"},
                                  "sensitive", "rescue", at=now)
                except Exception as exc:
                    log.debug("Sentinel ask_person audit error: %s", exc)
            elif act_type == "alert_family":
                tier = str(a.get("tier", 0))
                try:
                    record.record("system.alert", record.NUXIVA, "sentinel.rescue.escalate",
                                  {"tier": tier, "hazard": hazard}, "sensitive", "rescue", at=now)
                except Exception as exc:
                    log.debug("Sentinel alert_family audit error: %s", exc)
            elif act_type == "alert_emergency_contacts":
                rnd = str(a.get("round", 1))
                try:
                    record.record("system.alert", record.NUXIVA, "sentinel.rescue.escalate",
                                  {"tier": f"emergency_{rnd}", "hazard": hazard},
                                  "sensitive", "rescue", at=now)
                except Exception as exc:
                    log.debug("Sentinel emergency audit error: %s", exc)
            elif act_type == "home_alarm":
                try:
                    RedAlert().trigger("rescue.home_alarm")
                except Exception as exc:
                    log.debug("RedAlert trigger error: %s", exc)
                try:
                    record.record("system.alert", record.NUXIVA, "sentinel.rescue.alert",
                                  {"hazard": "fire", "source": "rescue", "confidence": "95"},
                                  "sensitive", "rescue", at=now)
                except Exception as exc:
                    log.debug("Sentinel home_alarm audit error: %s", exc)
            elif act_type == "stand_down":
                try:
                    RedAlert().stop()
                except Exception as exc:
                    log.debug("RedAlert stop error: %s", exc)
                try:
                    record.record("system.recovered", record.NUXIVA, "sentinel.rescue.stand_down",
                                  {"hazard": hazard}, "sensitive", "rescue", at=now)
                except Exception as exc:
                    log.debug("Sentinel stand_down audit error: %s", exc)


coordinator = RescueCoordinator()
