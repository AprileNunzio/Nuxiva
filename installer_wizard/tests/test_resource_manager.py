import time
import unittest
from unittest import mock

import resource_manager as rm

SYSTEM = {"mem_total": 16 << 30, "mem_available": 256 << 20, "swap_total": 0, "swap_used": 0, "cpu_percent": 10.0,
          "gpu_percent": 0.0, "gpu_mem_total": 0, "gpu_mem_used": 0}


def manager(groups=None, models=None):
    m = rm.ResourceManager()
    patches = [mock.patch.object(rm, "groups", return_value=groups or {}), mock.patch.object(rm, "loaded_models", return_value=models or []),
               mock.patch.object(rm, "system_sample", return_value=dict(SYSTEM)), mock.patch.object(rm, "release_heap")]
    for p in patches:
        p.start()
        m._p = getattr(m, "_p", []) + [p]
    return m


class Reports(unittest.TestCase):
    def tearDown(self):
        mock.patch.stopall()

    def test_clean_report_filters_garbage(self):
        clean = rm.clean_report({"device": "abcdef12", "js_heap_mb": 90, "surfaces": [
            {"id": "avatar3d", "mb": 300, "visible": True}, {"id": "bad id", "mb": 1}, {"id": "x", "mb": -5}, {"id": "y", "mb": True}, 7]})
        self.assertEqual([s["id"] for s in clean["surfaces"]], ["avatar3d"])
        self.assertIsNone(rm.clean_report({"device": "no"}))
        self.assertIsNone(rm.clean_report([]))

    def test_hidden_surface_gets_suspend_directive(self):
        m = manager()
        m.report(rm.clean_report({"device": "dev12345", "surfaces": [
            {"id": "defense-3d", "mb": 400, "visible": False}, {"id": "avatar3d", "mb": 200, "visible": True}, {"id": "voice", "mb": 50, "visible": False}]}))
        m.evaluate()
        d = m.directive_for("dev12345")
        self.assertEqual(d["suspend"], ["defense-3d"])
        self.assertNotIn("voice", d["suspend"] + d["hibernate"])

    def test_protected_process_never_actioned(self):
        m = manager(groups={"nuxiva-core": {"rss": 9 << 30, "cpu_percent": 90.0, "count": 3}})
        out = m.evaluate()
        self.assertEqual(out["level"], "critical")
        self.assertEqual(out["applied"], [])

    def test_idle_model_unloaded(self):
        models = [{"name": "llama3:8b", "size": 5 << 30, "expires_at": "2000-01-01T00:00:00Z"}]
        m = manager(models=models)
        with mock.patch.object(rm, "unload_model", return_value=True) as unload:
            out = m.evaluate()
        unload.assert_called_once_with("llama3:8b")
        self.assertTrue(any(a["action"] == "unload" and a["ok"] for a in out["applied"]))

    def test_clients_bounded_and_expire(self):
        m = manager()
        for i in range(40):
            m.report(rm.clean_report({"device": f"device{i:04d}", "surfaces": []}))
        self.assertEqual(len(m.clients), rm.MAX_DEVICES)
        for c in m.clients.values():
            c["at"] = time.monotonic() - rm.CLIENT_TTL - 1
        m.evaluate()
        self.assertEqual(len(m.clients), 0)


if __name__ == "__main__":
    unittest.main()
