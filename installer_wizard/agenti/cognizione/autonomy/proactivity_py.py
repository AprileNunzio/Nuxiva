import json

from agenti.autonomy import proactivity_schema as sc
from agenti.autonomy.proactivity_schema import HOUR_MS, fail

LEVEL_RANK = {name: index for index, name in enumerate(sc.LEVELS)}
LOWER = {"do_and_tell": "propose", "propose": "notify", "notify": "silent", "silent": "silent"}


def lk(rule: str, person) -> str:
    return f"{rule}|{person or ''}"


def reason(code: str, **params) -> dict:
    return {"code": f"proactive.why.{code}", "params": {k: str(v) for k, v in params.items()}}


def faded(rec: dict, now: int) -> dict:
    shift = min((max(0, now - rec["touched"])) // sc.FADE_MS, 8)
    return {**rec, "pos": rec["pos"] >> shift, "neg": rec["neg"] >> shift}


def posterior(rec: dict) -> int:
    return (rec["pos"] + 4) * 1000 // (rec["pos"] + rec["neg"] + 8)


class PyProactivity:
    def __init__(self, settings_json: str, rules_json: str, state_json: str | None = None) -> None:
        self.settings = sc.load_settings(settings_json)
        self.rules = sc.load_rules(rules_json)
        self.facts: dict = {}
        self.habits: dict = {}
        self.learner: dict = {}
        self.policies: dict = {}
        self.approved: set = set()
        self.pending_: list = []
        self.log_: list = []
        self.deferred: list = []
        self.undo_: list = []
        self.cooldown: dict = {}
        self.global_: list = []
        self.people: dict = {}
        self.next_id = 1
        self.stats_ = {"surfaced": 0, "accepted": 0, "refused": 0, "undone": 0, "silent": 0, "capped": 0, "blocked": 0, "expired": 0}
        if state_json:
            self.import_state(state_json)

    def _push(self, queue: list, item, cap: int) -> None:
        if len(queue) >= cap:
            queue.pop(0)
        queue.append(item)

    def _multiplier(self, key: str, now: int) -> int:
        rec = self.learner.get(key)
        if rec is None:
            return 1000
        return max(250, min(1250, posterior(faded(rec, now)) * 2))

    def _feedback(self, key: str, kind: str, now: int) -> None:
        if key not in self.learner and len(self.learner) >= 8192:
            return
        rec = faded(self.learner.get(key, {"pos": 0, "neg": 0, "undone": 0, "ignored": 0, "muted_until": 0, "touched": 0}), now)
        rec["touched"] = now
        if kind == "accepted":
            rec["pos"] += 1
            rec["undone"] = max(0, rec["undone"] - 1)
        elif kind == "refused":
            rec["neg"] += 1
        elif kind == "undone":
            rec["neg"] += 2
            rec["undone"] += 1
        else:
            rec["ignored"] += 1
            if rec["ignored"] >= 3:
                rec["ignored"] = 0
                rec["neg"] += 1
        if rec["pos"] + rec["neg"] > 64:
            rec["pos"] = rec["pos"] * 3 // 4
            rec["neg"] = rec["neg"] * 3 // 4
        if rec["neg"] >= 5 and posterior(rec) <= 300:
            rec["muted_until"] = now + self.settings["mute_ms"]
        self.learner[key] = rec

    def _prune(self, now: int) -> None:
        ttl = self.settings["signal_ttl_ms"]
        self.facts = {k: f for k, f in self.facts.items() if now - f[1] <= ttl}
        self.cooldown = {k: u for k, u in self.cooldown.items() if u > now}
        self.undo_ = [u for u in self.undo_ if u["expires_at"] > now]

    def _holds(self, rule: dict, person, now: int) -> bool:
        for c in rule.get("when", []):
            who = person if c.get("same_person") else None
            fact = self.facts.get(f"{c['domain']}|{c['key']}|{who or ''}")
            value = fact[0] if fact is not None and now - fact[1] <= self.settings["signal_ttl_ms"] else None
            if not self._test(c, value):
                return False
        return True

    @staticmethod
    def _test(c: dict, value) -> bool:
        cmp = c["cmp"]
        t = c.get("threshold", 0)
        if cmp == "present":
            return value is not None
        if cmp == "absent":
            return value is None
        if value is None:
            return False
        return value >= t if cmp == "ge" else value <= t if cmp == "le" else value == t

    def _task(self, rid: str, rule: dict, subject: str):
        a = rule["action"]
        task = {"schema_version": 1, "id": f"pro.{rid}.{self.next_id}", "parent": None, "kind": a["kind"], "class": a["class"], "priority": a["priority"],
                "deps": [], "scope": list(a.get("scope", [])), "budget": dict(a["budget"]), "risk_max": a["risk_max"],
                "input_ref": a["input_template"].replace("{subject}", subject), "idem_key": None}
        return task if sc.ident(task["id"]) and len(task["input_ref"]) <= 512 and not any(ord(c) < 32 for c in task["input_ref"]) else None

    def _register_undo(self, d: dict, now: int) -> None:
        rule = self.rules.get(d["rule"])
        undo = rule["action"].get("undo") if rule else None
        if undo is None:
            return
        a = rule["action"]
        task = {"schema_version": 1, "id": f"pro.undo.{d['rule']}.{d['id']}", "parent": d["action"]["id"] if d["action"] else None, "kind": undo["kind"],
                "class": a["class"], "priority": a["priority"], "deps": [], "scope": list(a.get("scope", [])), "budget": dict(a["budget"]),
                "risk_max": a["risk_max"], "input_ref": undo["input_template"].replace("{subject}", d["subject"]), "idem_key": None}
        if sc.ident(task["id"]) and len(task["input_ref"]) <= 512 and not any(ord(c) < 32 for c in task["input_ref"]):
            self._push(self.undo_, {"id": d["id"], "rule": d["rule"], "person": d["person"], "task": task, "expires_at": now + undo["window_ms"]}, 64)

    def _gate(self, privacy: str, person, ctx: dict) -> str:
        if privacy == "public":
            return "allow"
        if privacy == "household":
            return "redact" if ctx["guests_present"] else "allow"
        alone = not ctx["guests_present"] and len(ctx["present"]) == 1 and person is not None and ctx["present"][0] == person
        return "allow" if alone else "block"

    def _charged(self, person, now: int) -> tuple:
        self.global_ = [t for t in self.global_ if now - t < HOUR_MS]
        queue = self.people.get(person) if person else None
        if queue is not None:
            queue[:] = [t for t in queue if now - t < HOUR_MS]
        return len(self.global_), len(queue) if queue else 0

    def _charge(self, person, now: int) -> None:
        self.global_.append(now)
        if person and (len(self.people) < 1024 or person in self.people):
            self.people.setdefault(person, []).append(now)
        for name in list(self.people):
            self.people[name] = [t for t in self.people[name] if now - t < HOUR_MS]
            if not self.people[name]:
                del self.people[name]

    def _confidence(self, req: dict, rule: dict, key: str, now: int, reasons: list):
        origin, p = req["origin"]
        if origin == "signal":
            reasons.append(reason("signal", domain=rule["trigger"]["domain"], key=rule["trigger"]["key"], subject=req["subject"]))
            base = rule["base_confidence"]
        elif origin == "habit":
            reasons.append(reason("habit", permille=p))
            base = p * rule["base_confidence"] // 1000
        else:
            reasons.append(reason("forecast", permille=p))
            base = p
        mult = self._multiplier(key, now)
        if mult >= 1100:
            reasons.append(reason("learned_up", multiplier=mult))
        elif mult <= 900:
            reasons.append(reason("learned_down", multiplier=mult))
        return min(1000, base * mult // 1000), origin

    def _effective(self, rule: dict, policy) -> str:
        floor = {"health": "private", "email": "private", "security": "household"}.get(rule["domain"], "public")
        level = max(rule["privacy"], floor, key=sc.PRIVACY.index)
        return "private" if policy and rule["domain"] in policy["sealed"] else level

    def _mode(self, rule: dict, rid: str, key: str, redacted: bool, ctx: dict, critical: bool, reasons: list):
        level = rule["level"]
        steps = self.learner.get(key, {"undone": 0})["undone"] // 2
        for _ in range(steps):
            level = LOWER[level]
        if steps > 0 and rule["level"] != level:
            reasons.append(reason("level_lowered", steps=steps))
        if redacted:
            reasons.append(reason("privacy_redact"))
            if not critical and LEVEL_RANK[level] > 1:
                level = "notify"
        a = rule["action"]
        if level == "do_and_tell":
            if rid in self.approved and sc.RISKS.index(a["risk_max"]) <= 1 and a.get("undo") is not None:
                reasons.append(reason("auto_approved"))
            else:
                reasons.append(reason("needs_approval"))
                level = "propose"
        if level == "propose" and sc.RISKS.index(a["risk_max"]) >= 2:
            reasons.append(reason("consent_needed"))
        if level == "silent":
            return "diary", False, level
        if level == "do_and_tell":
            return "execute", False, level
        if ctx["voice_free"] and not redacted and (ctx["situation"] == "idle" or critical):
            reasons.append(reason("mode_speak"))
            return "speak", False, level
        reasons.append(reason("mode_widget"))
        return "widget", False, level

    def _run(self, req: dict, ctx: dict, now: int, retry):
        rid = req["rule"]
        rule = self.rules.get(rid)
        if rule is None:
            return None
        _day, weekday, minute = sc.local(now, ctx["tz_offset_min"])
        w = rule.get("window")
        if w is not None and not (w.get("weekdays", 127) >> weekday & 1 and sc.in_span(minute, w["start_min"], w["end_min"])):
            return None
        person = req["person"]
        if not self._holds(rule, person, now):
            return None
        key = lk(rid, person)
        critical = rule["urgency"] == "critical"
        reasons: list = []
        if w is not None:
            reasons.append(reason("window"))
        if rule.get("when"):
            reasons.append(reason("conditions", count=len(rule["when"])))
        if critical:
            reasons.append(reason("critical"))
        confidence, origin = self._confidence(req, rule, key, now, reasons)
        policy = self.policies.get(person) if person else None
        verdict = self._gate(self._effective(rule, policy), person, ctx)
        redacted = verdict == "redact"
        cost = 0 if critical else self.settings["cost_" + ctx["situation"]]
        score = rule["value"] * confidence // 1000 - cost
        quiet = sc.in_span(minute, self.settings["quiet_start_min"], self.settings["quiet_end_min"])
        rec = self.learner.get(key)
        kind, why = "surface", None
        if not critical and policy and rule["domain"] in policy["muted"]:
            kind, why = "silent", reason("muted_by_person")
        elif not critical and rec and rec["muted_until"] > now:
            kind, why = "silent", reason("muted_by_feedback")
        elif confidence < rule["min_confidence"]:
            kind, why = "silent", reason("low_confidence", confidence=confidence, threshold=rule["min_confidence"])
        elif verdict == "block":
            kind, why = "defer", reason("privacy_block")
        elif not critical and quiet:
            kind, why = "defer", reason("quiet_hours")
        elif score <= 0:
            kind, why = "defer", reason("cost", cost=cost)
        else:
            glob, per = self._charged(person, now)
            if not critical and glob >= self.settings["hourly_cap"]:
                kind, why = "defer", reason("cap_global", cap=self.settings["hourly_cap"])
            elif not critical and per >= self.settings["person_hourly_cap"]:
                kind, why = "defer", reason("cap_person", cap=self.settings["person_hourly_cap"])
        if redacted:
            for r in reasons:
                r["params"].pop("subject", None)
        expires = retry if retry is not None else now + self.settings["proposal_ttl_ms"]
        deferred = False
        if kind == "silent":
            reasons.append(why)
            mode, level = "diary", "silent"
        elif kind == "defer":
            if retry is None:
                self.stats_["blocked" if why["code"].endswith("privacy_block") else "capped"] += 1
            reasons.append(why)
            self._push(self.deferred, {"request": req, "expires_at": expires}, self.settings["deferred_cap"])
            mode, deferred, level = "diary", True, "silent"
        else:
            mode, _unused, level = self._mode(rule, rid, key, redacted, ctx, critical, reasons)
        if deferred and retry is not None:
            return None
        if mode == "diary" and not deferred:
            self.stats_["silent"] += 1
        hidden = redacted and not critical
        action = None if mode == "diary" or hidden or level == "notify" else self._task(rid, rule, req["subject"])
        a = rule["action"]
        decision = {
            "id": self.next_id, "rule": rid, "person": person, "summary_key": "proactive.redacted" if redacted else rule["summary_key"],
            "subject": "" if redacted else req["subject"], "action": action, "mode": mode, "confidence": confidence, "score": score,
            "requires_consent": mode != "execute" and action is not None and sc.RISKS.index(a["risk_max"]) >= 2,
            "redacted": redacted, "deferred": deferred,
            "undoable": a.get("undo") is not None and mode != "diary" and LEVEL_RANK[level] >= 2,
            "created_at": now, "expires_at": expires,
            "explanation": {"rule": rid, "origin": origin, "confidence": confidence, "threshold": rule["min_confidence"], "score": score, "reasons": reasons},
        }
        self.next_id += 1
        self._push(self.log_, decision, self.settings["log_cap"])
        if mode == "execute":
            self._charge(person, now)
            self.stats_["surfaced"] += 1
            self._register_undo(decision, now)
        elif mode in ("widget", "speak"):
            self._charge(person, now)
            self.stats_["surfaced"] += 1
            self._push(self.pending_, decision, self.settings["pending_cap"])
        return decision

    def ingest(self, signal_json: str, context_json: str, now: int) -> str:
        sig = sc.parse_signal(signal_json)
        ctx = sc.parse_context(context_json)
        if not sc.signal_valid(sig):
            fail("invalid")
        self._prune(now)
        fkey = f"{sig['domain']}|{sig['key']}|{sig['person'] or ''}"
        if len(self.facts) < 4096 or fkey in self.facts:
            self.facts[fkey] = (sig["value"], min(sig["at"], now))
        out = []
        for rid in sorted(self.rules):
            rule = self.rules[rid]
            t = rule["trigger"]
            if t["domain"] != sig["domain"] or t["key"] != sig["key"] or not self._test(t, sig["value"]):
                continue
            person = sig["person"] if rule["audience"] == "subject" else None
            if rule["audience"] == "subject" and person is None:
                continue
            cool = f"s|{lk(rid, person)}|{sig['subject']}"
            if self.cooldown.get(cool, 0) > now:
                continue
            req = {"rule": rid, "person": person, "subject": sig["subject"], "origin": ("signal", 0)}
            decision = self._run(req, ctx, now, None)
            if decision is not None:
                if len(self.cooldown) < 8192:
                    self.cooldown[cool] = now + max(rule.get("cooldown_ms", 0), self.settings["dedupe_ms"])
                out.append(decision)
        return json.dumps(out)

    def forecast(self, forecast_json: str, context_json: str, now: int) -> str:
        f = sc.parse_forecast(forecast_json)
        ctx = sc.parse_context(context_json)
        if not sc.forecast_valid(f):
            fail("invalid")
        rule = self.rules.get(f["rule"])
        if rule is None:
            fail("not_found")
        if rule["audience"] == "subject" and f["person"] is None:
            fail("invalid")
        person = f["person"] if rule["audience"] == "subject" else None
        self._prune(now)
        cool = f"f|{lk(f['rule'], person)}|{f['subject']}"
        if self.cooldown.get(cool, 0) > now:
            return "[]"
        if len(self.cooldown) < 8192:
            self.cooldown[cool] = now + self.settings["dedupe_ms"]
        req = {"rule": f["rule"], "person": person, "subject": f["subject"], "origin": ("forecast", f["probability"])}
        decision = self._run(req, ctx, now, None)
        return json.dumps([decision] if decision else [])

    def tick(self, context_json: str, now: int) -> str:
        ctx = sc.parse_context(context_json)
        self._prune(now)
        live = [d for d in self.pending_ if d["expires_at"] > now]
        for d in [d for d in self.pending_ if d["expires_at"] <= now]:
            self.stats_["expired"] += 1
            self._feedback(lk(d["rule"], d["person"]), "ignored", now)
        self.pending_ = live
        waiting, self.deferred = self.deferred, []
        out = []
        for item in waiting:
            if item["expires_at"] <= now:
                continue
            decision = self._run(item["request"], ctx, now, item["expires_at"])
            if decision is not None:
                out.append(decision)
        return json.dumps(out)

    def _take(self, pid: int) -> dict:
        for index, d in enumerate(self.pending_):
            if d["id"] == pid:
                return self.pending_.pop(index)
        fail("not_found")

    def accept(self, pid: int, now: int) -> str:
        found = next((d for d in self.pending_ if d["id"] == pid), None)
        if found is None:
            fail("not_found")
        if found["action"] is None:
            fail("state")
        d = self._take(pid)
        key = lk(d["rule"], d["person"])
        if d["expires_at"] <= now:
            self.stats_["expired"] += 1
            self._feedback(key, "ignored", now)
            fail("expired")
        self.stats_["accepted"] += 1
        self._feedback(key, "accepted", now)
        self._register_undo(d, now)
        return json.dumps(d["action"])

    def refuse(self, pid: int, now: int) -> None:
        d = self._take(pid)
        self._feedback(lk(d["rule"], d["person"]), "refused", now)
        self.stats_["refused"] += 1

    def dismiss(self, pid: int) -> None:
        self._take(pid)

    def undo(self, pid: int, now: int) -> str:
        for index, u in enumerate(self.undo_):
            if u["id"] == pid:
                entry = self.undo_.pop(index)
                if entry["expires_at"] <= now:
                    fail("expired")
                self._feedback(lk(entry["rule"], entry["person"]), "undone", now)
                self.stats_["undone"] += 1
                return json.dumps(entry["task"])
        fail("not_found")

    def approve_always(self, rule: str) -> None:
        found = self.rules.get(rule)
        if found is None:
            fail("not_found")
        if sc.RISKS.index(found["action"]["risk_max"]) > 1 or found["action"].get("undo") is None:
            fail("consent")
        self.approved.add(rule)

    def revoke(self, rule: str) -> None:
        self.approved.discard(rule)

    def set_policy(self, person: str, policy_json: str) -> None:
        raw = sc.load_json(policy_json)
        if not sc.keys(raw, (), ("muted", "sealed")) or not all(isinstance(raw.get(k, []), list) and all(x in sc.DOMAINS for x in raw.get(k, [])) for k in ("muted", "sealed")):
            fail("parse")
        if not sc.person_ok(person) or (len(self.policies) >= 256 and person not in self.policies):
            fail("invalid")
        self.policies[person] = {"muted": set(raw.get("muted", [])), "sealed": set(raw.get("sealed", []))}

    def reset_learning(self, rule: str, person=None) -> None:
        self.learner.pop(lk(rule, person), None)

    def pending(self) -> str:
        return json.dumps(self.pending_)

    def log(self) -> str:
        return json.dumps(self.log_)

    def explain(self, pid: int) -> str:
        for d in self.pending_ + self.log_:
            if d["id"] == pid:
                return json.dumps(d["explanation"])
        fail("not_found")

    def undoable(self) -> str:
        return json.dumps([u["id"] for u in self.undo_])

    def stats(self) -> str:
        s = self.stats_
        decided = s["accepted"] + s["refused"] + s["undone"]
        return json.dumps({**s, "acceptance_permille": s["accepted"] * 1000 // decided if decided else None})

    def export_state(self) -> str:
        policies = {p: {"muted": sorted(v["muted"]), "sealed": sorted(v["sealed"])} for p, v in sorted(self.policies.items())}
        return json.dumps({"learner": dict(sorted(self.learner.items())), "habits": self.habits, "policies": policies, "approved": sorted(self.approved)}, separators=(",", ":"))

    def import_state(self, text: str) -> None:
        if len(text) > sc.MAX_PAYLOAD:
            fail("too_large")
        try:
            state = json.loads(text)
        except ValueError:
            fail("parse")
        if not sc.keys(state, ("learner", "habits", "policies", "approved")):
            fail("parse")
        approved = state["approved"]
        safe = isinstance(approved, list) and all(
            a in self.rules and sc.RISKS.index(self.rules[a]["action"]["risk_max"]) <= 1 and self.rules[a]["action"].get("undo") is not None for a in approved)
        learner = state["learner"]
        fields = ("pos", "neg", "undone", "ignored", "muted_until", "touched")
        learner_ok = isinstance(learner, dict) and len(learner) <= 8192 and all(
            sc.keys(r, fields) and all(sc.integer(v) and v >= 0 for v in r.values()) and len(k) <= 160 for k, r in learner.items())
        habits_ok = isinstance(state["habits"], dict) and len(state["habits"]) <= 4096 and all(
            k.split("|")[0] in self.rules and self.rules[k.split("|")[0]].get("habit") for k in state["habits"])
        policies = state["policies"]
        pol_ok = isinstance(policies, dict) and len(policies) <= 256 and all(
            sc.keys(v, (), ("muted", "sealed")) and all(x in sc.DOMAINS for k in ("muted", "sealed") for x in v.get(k, [])) for v in policies.values())
        if not (safe and learner_ok and habits_ok and pol_ok):
            fail("invalid")
        self.learner = learner
        self.habits = state["habits"]
        self.policies = {p: {"muted": set(v.get("muted", [])), "sealed": set(v.get("sealed", []))} for p, v in policies.items()}
        self.approved = set(approved)
