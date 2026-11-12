import random
import unittest

import native_core

from agenti.rescue import engine
from agenti.rescue.policy import PolicyError, parse
from agenti.rescue.signals import KINDS, EvidenceError

SOURCES = ("cam1", "cam2", "mic1", "mic2", "watch", "ha.smoke", "voice")
NATIVE = native_core.symbol("RustRescue") is not None


def close(test, a, b, path="") -> None:
    if isinstance(a, float) or isinstance(b, float):
        test.assertAlmostEqual(float(a), float(b), places=9, msg=path)
    elif isinstance(a, dict):
        test.assertEqual(set(a), set(b), path)
        for key in a:
            close(test, a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list):
        test.assertEqual(len(a), len(b), path)
        for i, (x, y) in enumerate(zip(a, b)):
            close(test, x, y, f"{path}[{i}]")
    else:
        test.assertEqual(a, b, path)


def py(policy=""):
    return engine.Rescue(policy, prefer_native=False)


def kinds(step) -> list[str]:
    return [a["type"] for a in step["actions"]]


class RescueFallbackTest(unittest.TestCase):
    def test_fall_and_stillness_ask_first(self):
        r = py()
        r.observe("fall", 0.9, 0.8, "cam1", 0.0, 0.0)
        self.assertEqual(r.update(0.0)["stage"], "watching")
        r.observe("immobility", 0.9, 0.8, "cam1", 1.0, 1.0)
        step = r.update(1.0)
        self.assertEqual(step["stage"], "check_in")
        self.assertEqual(kinds(step), ["ask_person"])

    def test_silence_escalates_then_bounded_emergency(self):
        r = py()
        r.observe("fall", 0.9, 0.8, "cam1", 0.0, 0.0)
        r.observe("immobility", 0.9, 0.8, "cam1", 0.0, 0.0)
        r.update(0.0)
        self.assertIn("alert_family", kinds(r.update(31.0)))
        self.assertIn("alert_family", kinds(r.update(152.0)))
        step = r.update(273.0)
        self.assertEqual(step["stage"], "emergency")
        rounds = 1 + sum(kinds(r.update(273.0 + 181.0 * i)).count("alert_emergency_contacts") for i in range(1, 20))
        self.assertEqual(rounds, 3)

    def test_person_ok_stands_down(self):
        r = py()
        r.need_help(0.0)
        step = r.person_ok(4.0)
        self.assertEqual(step["actions"][0], {"type": "stand_down", "hazard": "medical", "notified_tiers": 1, "emergency": False})

    def test_smoke_does_not_wait_and_ok_does_not_cancel_fire(self):
        r = py()
        r.observe("smoke", 0.95, 1.0, "ha.smoke", 0.0, 0.0)
        step = r.update(0.0)
        self.assertIn("home_alarm", kinds(step))
        self.assertEqual(r.person_ok(1.0)["actions"], [])
        self.assertIn("stand_down", kinds(r.dismiss(2.0)))

    def test_invalid_input_is_rejected(self):
        r = py()
        with self.assertRaises(EvidenceError):
            r.observe("fall", 2.0, 0.5, "cam1", 0.0, 0.0)
        with self.assertRaises(EvidenceError):
            r.observe("unlock", 0.5, 0.5, "cam1", 0.0, 0.0)
        with self.assertRaises(EvidenceError):
            r.observe("fall", 0.5, 0.5, "cam 1", 0.0, 0.0)
        with self.assertRaises(EvidenceError):
            r.update(float("nan"))
        with self.assertRaises(PolicyError):
            parse('{"unlock_doors": true}')
        with self.assertRaises(PolicyError):
            parse('{"watch": 0.5, "check": 0.4}')


def scenario(seed: int) -> list[tuple]:
    rnd = random.Random(seed)
    now, ops = 0.0, []
    for _ in range(80):
        now += rnd.choice((0.0, 0.5, 3.0, 15.0, 40.0, 130.0, 200.0))
        pick = rnd.random()
        if pick < 0.6:
            ops.append(("observe", rnd.choice(KINDS), round(rnd.random(), 3), round(rnd.random(), 3),
                        rnd.choice(SOURCES), max(0.0, now - rnd.choice((0.0, 2.0, 30.0))), now))
        elif pick < 0.8:
            ops.append(("update", now))
        elif pick < 0.87:
            ops.append(("person_ok", now))
        elif pick < 0.92:
            ops.append(("need_help", now))
        elif pick < 0.96:
            ops.append(("acknowledge", rnd.randint(0, 3), now))
        else:
            ops.append(("dismiss", now))
    return ops


@unittest.skipUnless(NATIVE, "modulo nativo assente")
class RescueParityTest(unittest.TestCase):
    def test_engine_parity_on_random_scenarios(self):
        for policy in ("", '{"sensitivity": "high", "family_tiers": 3}', '{"sensitivity": "low", "reliability": {"fall": 0.95}}'):
            for seed in range(60):
                rust, python = engine.Rescue(policy), py(policy)
                self.assertTrue(rust.native)
                for op in scenario(seed):
                    name, args = op[0], op[1:]
                    if name == "observe":
                        rust.observe(*args)
                        python.observe(*args)
                        continue
                    close(self, getattr(rust, name)(*args), getattr(python, name)(*args), f"{seed}:{op}")
                close(self, rust.timeline(), python.timeline(), f"{seed}:timeline")

    def test_assess_parity(self):
        rnd = random.Random(7)
        for _ in range(300):
            items = [{"kind": rnd.choice(KINDS), "probability": rnd.random(), "confidence": rnd.random(),
                      "source": rnd.choice(SOURCES), "room": None, "at": rnd.uniform(0.0, 100.0)} for _ in range(rnd.randint(0, 12))]
            close(self, engine.assess(items, 100.0), engine.assess(items, 100.0, prefer_native=False))

    def test_policy_parity(self):
        for raw in ("", '{"watch": 0.5, "check": 0.4}', '{"unlock_doors": 1}', '{"family_tiers": 0}',
                    '{"reliability": {"fall": 2}}', '{"check_in_s": 5}', '{"sensitivity": "high"}'):
            outcomes = []
            for prefer in (True, False):
                try:
                    engine.Rescue(raw, prefer_native=prefer)
                    outcomes.append("ok")
                except ValueError as exc:
                    outcomes.append(str(exc))
            self.assertEqual(outcomes[0], outcomes[1], raw)

    def test_native_rejects_bad_evidence(self):
        r = engine.Rescue()
        for args in (("fall", 2.0, 0.5, "cam1", 0.0, 0.0), ("unlock", 0.5, 0.5, "cam1", 0.0, 0.0),
                     ("fall", 0.5, 0.5, "x" * 200, 0.0, 0.0), ("fall", 0.5, 0.5, "cam1", 99.0, 0.0)):
            with self.assertRaises(ValueError):
                r.observe(*args)


if __name__ == "__main__":
    unittest.main()
