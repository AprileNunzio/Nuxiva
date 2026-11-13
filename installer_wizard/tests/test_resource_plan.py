import json
import random
import unittest

import resource_plan as rp

GB = 1 << 30
KINDS = list(rp.KINDS)
CLASSES = list(rp.CLASSES)
LEVELS = [None, *rp.LEVELS]


def system(avail_mb, cpu=0.0, gpu=0.0):
    return {"mem_total": 16 * GB, "mem_available": avail_mb * 1048576, "cpu_percent": cpu, "gpu_percent": gpu}


def comp(ident, kind="cache", cls="low", rss=0, **extra):
    return {"id": ident, "kind": kind, "class": cls, "rss": rss, "reclaimable": True, **extra}


def scenario(rng):
    comps = []
    for i in range(rng.randint(0, 24)):
        comps.append({"id": f"c{i}", "kind": rng.choice(KINDS), "class": rng.choice(CLASSES),
                      "rss": rng.randint(0, 6 * GB), "budget": rng.choice([None, None, rng.randint(0, 4 * GB)]),
                      "idle_ms": rng.choice([0, 1000, 40_000, 200_000, 700_000, 2_000_000]),
                      "visible": rng.random() < 0.5, "reclaimable": rng.random() < 0.7,
                      "cpu_percent": rng.choice([0.0, 20.0, 50.0, 90.5])})
    sysd = {"mem_total": rng.choice([4, 8, 16, 32]) * GB, "cpu_percent": rng.choice([0.0, 30.0, 80.0, 99.9]),
            "gpu_percent": rng.choice([0.0, 50.0, 95.0]), "swap_total": rng.choice([0, 4 * GB]),
            "gpu_mem_total": rng.choice([0, 8 * GB]), "cores": rng.choice([0, 2, 4, 8, 16])}
    sysd["mem_available"] = rng.randint(0, sysd["mem_total"] + GB)
    sysd["swap_used"] = rng.randint(0, sysd["swap_total"] + 1)
    sysd["gpu_mem_used"] = rng.randint(0, sysd["gpu_mem_total"] + 1)
    return {"system": sysd, "components": comps, "previous": rng.choice(LEVELS)}


class PlanBehaviour(unittest.TestCase):
    def test_hidden_surface_suspended_when_calm(self):
        out = rp.plan_python(json.dumps({"system": system(14000), "components": [comp("s", "surface", "normal", GB, visible=False)]}))
        self.assertEqual(out["level"], "calm")
        self.assertEqual([a["action"] for a in out["actions"]], ["suspend"])

    def test_protected_never_touched(self):
        out = rp.plan_python(json.dumps({"system": system(0), "components": [
            comp("voice", "process", "protected", 8 * GB, idle_ms=10**9, visible=False)]}))
        self.assertEqual(out["level"], "critical")
        self.assertEqual(out["actions"], [])
        self.assertEqual(out["protected"], ["voice"])

    def test_idle_model_unloaded_under_pressure_only(self):
        model = comp("m", "model", "normal", 4 * GB, idle_ms=200_000, visible=False)
        calm = rp.plan_python(json.dumps({"system": system(14000), "components": [model]}))
        high = rp.plan_python(json.dumps({"system": system(1024), "components": [model]}))
        self.assertEqual(calm["actions"], [])
        self.assertEqual(high["actions"][0]["action"], "unload")

    def test_idle_limit_scales_with_machine_power(self):
        model = comp("m", "model", "normal", GB, idle_ms=2_000_000, visible=False)
        weak = {"mem_total": 4 * GB, "mem_available": 3 * GB, "cores": 2}
        strong = {"mem_total": 32 * GB, "mem_available": 28 * GB, "cores": 16}
        out_weak = rp.plan_python(json.dumps({"system": weak, "components": [model]}))
        out_strong = rp.plan_python(json.dumps({"system": strong, "components": [model]}))
        self.assertEqual([a["action"] for a in out_weak["actions"]], ["unload"])
        self.assertEqual(out_strong["actions"], [])

    def test_hysteresis(self):
        held = rp.plan_python(json.dumps({"system": system(2560), "previous": "high"}))
        fresh = rp.plan_python(json.dumps({"system": system(2560)}))
        self.assertEqual((fresh["level"], held["level"]), ("elevated", "high"))

    def test_invalid_input_rejected(self):
        for bad in ("{", "[]", json.dumps({"system": {"mem_total": 0, "mem_available": 0}}),
                    json.dumps({"system": system(10), "components": [comp("BAD ID")]}),
                    json.dumps({"system": system(10), "components": [comp("a", rss=-1)]}),
                    json.dumps({"system": system(10), "components": [comp("a", kind="x")]}),
                    json.dumps({"system": system(10), "previous": "nope"})):
            with self.assertRaises(ValueError):
                rp.plan_python(bad)
        with self.assertRaises(ValueError):
            rp.plan_python(" " * (rp.MAX_INPUT + 1))


@unittest.skipUnless(rp.native_available(), "motore nativo assente")
class Parity(unittest.TestCase):
    def test_native_matches_python(self):
        import nuxiva_native
        rng = random.Random(20261113)
        for _ in range(400):
            raw = json.dumps(scenario(rng), separators=(",", ":"))
            self.assertEqual(json.loads(nuxiva_native.resource_plan(raw)), rp.plan_python(raw), raw)

    def test_native_rejects_what_python_rejects(self):
        import nuxiva_native
        for bad in ("{", "[]", json.dumps({"system": {"mem_total": 0, "mem_available": 0}}),
                    json.dumps({"system": system(10), "components": [comp("BAD ID")]})):
            with self.assertRaises(ValueError):
                nuxiva_native.resource_plan(bad)


if __name__ == "__main__":
    unittest.main()
