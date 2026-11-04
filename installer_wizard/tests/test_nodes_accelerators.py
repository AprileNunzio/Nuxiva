import unittest

from features.nodes import adapt

RK3588 = {"cores": 8, "ram_gb": 16, "audio_in": ["USB Mic"], "soc": {"vendor": "Rockchip", "family": "rk3588", "model": "Radxa ROCK 5B"},
          "cpu_features": ["neon", "dotprod", "<script>"],
          "accelerators": [{"id": "rknn", "vendor": "Rockchip", "kind": "npu", "ready": True, "runtime": "librknnrt.so",
                            "tasks": ["wake_word", "vision", "llm", "rm -rf"]}]}


class AcceleratorTest(unittest.TestCase):
    def test_accelerators_and_soc_are_whitelisted(self):
        clean = adapt.clean_hardware({**RK3588, "accelerators": RK3588["accelerators"] + [{"id": "../../x", "kind": "evil"}] * 20})
        self.assertEqual(clean["soc"], {"vendor": "Rockchip", "family": "rk3588", "model": "Radxa ROCK 5B"})
        self.assertEqual(clean["cpu_features"], ["dotprod", "neon", "script"])
        self.assertEqual(len(clean["accelerators"]), 8)
        first = clean["accelerators"][0]
        self.assertEqual(first, {"id": "rknn", "vendor": "Rockchip", "kind": "npu", "ready": True, "runtime": "librknnrt.so",
                                 "tasks": ["wake_word", "vision", "llm"]})
        self.assertEqual(clean["accelerators"][1]["id"], "x")
        self.assertEqual(clean["accelerators"][1]["kind"], "npu")
        self.assertEqual(adapt.clean_hardware({"accelerators": "no"})["accelerators"], [])

    def test_offload_plan_is_sanitized(self):
        raw = {"wake_word": {"target": "edge", "backend": "RKNN;drop"}, "stt": {"target": "server"},
               "vision": {"target": "unavailable", "reason": "no_camera"}, "llm": {"target": "mars"}, "evil": {"target": "edge"},
               "tts": "edge"}
        self.assertEqual(adapt.clean_offload(raw), {"wake_word": {"target": "edge", "backend": "rknndrop"}, "stt": {"target": "server"},
                                                    "vision": {"target": "unavailable", "reason": "no_camera"}})
        self.assertEqual(adapt.clean_offload(None), {})

    def test_accelerator_changes_and_missing_runtime_are_reported(self):
        before = adapt.clean_hardware({**RK3588, "accelerators": []})
        after = adapt.clean_hardware(RK3588)
        self.assertIn("Acceleratore collegato: Rockchip (rknn)", adapt.diff(before, after))
        self.assertIn("Acceleratore scollegato: Rockchip (rknn)", adapt.diff(after, before))
        missing = adapt.clean_hardware({**RK3588, "accelerators": [{**RK3588["accelerators"][0], "ready": False}]})
        self.assertIn("Acceleratore rknn senza runtime", adapt.diff(after, missing))
        self.assertTrue(any("senza runtime" in tip for tip in adapt.advice(missing)))
        self.assertFalse(any("senza runtime" in tip for tip in adapt.advice(after)))


if __name__ == "__main__":
    unittest.main()
