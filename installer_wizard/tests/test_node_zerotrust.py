import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import native_core

from agenti.nodes import audit as audit_module
from agenti.nodes import trustpolicy, zerotrust, zt_engine

VECTORS = json.loads((Path(__file__).resolve().parents[2] / "native/crates/node-core/tests/vectors.json").read_text(encoding="utf-8"))
NATIVE = native_core.symbol("node_authorize") is not None


def outcome(call):
    try:
        return {"ok": call()}
    except ValueError as exc:
        return {"error": str(exc)}


class EngineVectorsTest(unittest.TestCase):
    def test_mode(self):
        for case in VECTORS["mode"]:
            self.assertEqual(zt_engine.resolve_mode(*case["args"]), case["expect"], case)

    def test_effective(self):
        for case in VECTORS["effective"]:
            self.assertEqual(zt_engine.effective_scopes(*case["args"]), case["expect"], case)

    def test_authorize(self):
        for case in VECTORS["authorize"]:
            self.assertEqual(list(zt_engine.authorize(*case["args"])), case["expect"], case)

    def test_announce(self):
        for case in VECTORS["announce"]:
            got = outcome(lambda case=case: json.loads(zt_engine.parse_announce(case["raw"])))
            self.assertEqual(got, case["expect"], case["raw"][:60])

    def test_identity(self):
        keys, ident = VECTORS["keys"], VECTORS["identity"]
        self.assertEqual(zt_engine.fingerprint(keys["one"]), ident["fingerprint"])
        self.assertEqual(zt_engine.pairing_code(keys["one"]), ident["code"])
        self.assertEqual(zt_engine.fingerprint(keys["two"]), ident["fingerprint_two"])

    def test_verify(self):
        for case in VECTORS["verify"]:
            got = outcome(lambda case=case: zt_engine.verify_request(*case["args"]) or True)
            self.assertEqual(got, case["expect"], case["name"])

    def test_audit(self):
        for case in VECTORS["audit_seal"]:
            self.assertEqual(json.loads(zt_engine.audit_seal(*case["args"])), case["expect"])
        for case in VECTORS["audit_verify"]:
            self.assertEqual(zt_engine.audit_verify(case["anchor"], json.dumps(case["entries"])), case["expect"])


@unittest.skipUnless(NATIVE, "native module missing")
class NativeVectorsTest(unittest.TestCase):
    def test_native_matches_vectors(self):
        sym = native_core.symbol
        for case in VECTORS["mode"]:
            self.assertEqual(sym("node_resolve_mode")(*case["args"]), case["expect"])
        for case in VECTORS["effective"]:
            self.assertEqual(sym("node_effective_scopes")(*case["args"]), case["expect"])
        for case in VECTORS["authorize"]:
            self.assertEqual(list(sym("node_authorize")(*case["args"])), case["expect"])
        for case in VECTORS["announce"]:
            got = outcome(lambda case=case: json.loads(sym("node_parse_announce")(case["raw"])))
            self.assertEqual(got, case["expect"])
        for case in VECTORS["verify"]:
            got = outcome(lambda case=case: sym("node_verify_request")(*case["args"]) or True)
            self.assertEqual(got, case["expect"], case["name"])
        for case in VECTORS["audit_seal"]:
            self.assertEqual(json.loads(sym("node_audit_seal")(*case["args"])), case["expect"])
        for case in VECTORS["audit_verify"]:
            self.assertEqual(sym("node_audit_verify")(case["anchor"], json.dumps(case["entries"])), case["expect"])


class FacadeTest(unittest.TestCase):
    def test_facade_matches_engine_when_native_disabled(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            for case in VECTORS["authorize"]:
                self.assertEqual(list(zerotrust.authorize(*case["args"])), case["expect"])
            for case in VECTORS["mode"][:20]:
                self.assertEqual(zerotrust.resolve_mode(*case["args"]), case["expect"])
            self.assertEqual(zerotrust.fingerprint(VECTORS["keys"]["one"]), VECTORS["identity"]["fingerprint"])


class TrustPolicyTest(unittest.TestCase):
    def node(self, **extra):
        return {"id": "pc-uno", "pubkey": VECTORS["keys"]["one"], "profile": "satellite", "second_server_allowed": False,
                "grants": [], **extra}

    def announce(self, scopes, cores=8, ram=16384):
        return {"scopes": sorted(scopes), "rejected": [], "cpu_cores": cores, "ram_mb": ram, "full_host": "node.host_full" in scopes}

    def test_new_device_is_a_satellite_until_it_announces(self):
        state = trustpolicy.state(self.node())
        self.assertEqual((state["mode"], state["effective"], state["legacy"]), ("satellite", [], False))

    def test_satellite_profile_never_gets_server_scopes(self):
        announce = self.announce(["audio.capture", "compute.lease", "fs.read", "node.host_full"])
        state = trustpolicy.state(self.node(announce=announce))
        self.assertEqual(state["effective"], ["audio.capture"])
        self.assertIn("compute.lease", state["denied"])

    def test_second_server_requires_explicit_approval(self):
        announce = self.announce(["audio.capture", "compute.lease", "fs.write"])
        unapproved = trustpolicy.state(self.node(announce=announce, profile="second_server"))
        self.assertEqual(unapproved["mode"], "satellite")
        approved = trustpolicy.state(self.node(announce=announce, profile="second_server", second_server_allowed=True))
        self.assertEqual(approved["mode"], "second_server")
        self.assertEqual(approved["effective"], ["audio.capture", "compute.lease"])
        elevated = trustpolicy.state(self.node(announce=announce, profile="second_server", second_server_allowed=True, grants=["fs.write"]))
        self.assertIn("fs.write", elevated["effective"])

    def test_auto_needs_capable_hardware_and_host_announcement(self):
        full = self.announce(["audio.capture", "node.host_full", "agents.run"])
        node = self.node(announce=full, profile="auto", second_server_allowed=True)
        self.assertEqual(trustpolicy.state(node)["mode"], "second_server")
        weak = self.announce(["audio.capture", "node.host_full"], cores=2, ram=1024)
        self.assertEqual(trustpolicy.state({**node, "announce": weak})["mode"], "satellite")

    def test_legacy_nodes_stay_limited_and_cannot_become_second_server(self):
        legacy = {"id": "vecchio", "token": "x"}
        state = trustpolicy.state(legacy)
        self.assertTrue(state["legacy"])
        self.assertEqual(state["mode"], "satellite")
        self.assertIn("compute.lease", state["effective"])
        self.assertNotIn("agents.run", state["effective"])
        for args in (("second_server", True, []), ("auto", True, []), ("satellite", True, []), ("satellite", False, ["fs.write"])):
            with self.assertRaises(ValueError) as ctx:
                trustpolicy.validate_change(legacy, *args)
            self.assertEqual(str(ctx.exception), "node.error.legacy_identity")

    def test_validate_change_rules(self):
        node = self.node()
        self.assertEqual(trustpolicy.validate_change(node, "second_server", True, ["fs.write", "fs.write"]), ("second_server", True, ["fs.write"]))
        for args, code in ((("second_server", False, []), "node.error.ceiling_required"),
                           (("auto", False, []), "node.error.ceiling_required"),
                           (("satellite", False, ["fs.write"]), "node.error.ceiling_required"),
                           (("root", True, []), "node.error.profile"),
                           (("second_server", True, ["admin.users"]), "node.error.grant"),
                           (("second_server", True, [1]), "node.error.grant")):
            with self.assertRaises(ValueError) as ctx:
                trustpolicy.validate_change(node, *args)
            self.assertEqual(str(ctx.exception), code, args)


class AuditLogTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        self.log = audit_module.AuditLog(directory / "audit.jsonl", directory / "audit.anchor")
        self.directory = directory

    def test_chain_is_valid_and_persists(self):
        for index in range(5):
            self.log.record("admin", "pc-uno", "profile.set", f"v{index}")
        self.assertEqual(self.log.verify(), {"ok": True, "broken_at": None, "entries": 5})
        again = audit_module.AuditLog(self.directory / "audit.jsonl", self.directory / "audit.anchor")
        self.assertEqual(again.verify()["entries"], 5)
        self.assertEqual(again.record("admin", "pc-uno", "x")["seq"], 6)

    def test_tampering_on_disk_is_detected(self):
        for index in range(4):
            self.log.record("admin", "pc-uno", "profile.set", f"v{index}")
        path = self.directory / "audit.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace("v2", "v9"), encoding="utf-8")
        reloaded = audit_module.AuditLog(path, self.directory / "audit.anchor")
        self.assertEqual(reloaded.verify()["broken_at"], 2)

    def test_compaction_keeps_chain_verifiable(self):
        with mock.patch.object(audit_module, "KEEP", 20), mock.patch.object(audit_module, "SLACK", 5):
            for index in range(40):
                self.log.record("admin", "pc-uno", "tick", str(index))
            self.assertLessEqual(len(self.log.entries), 25)
            self.assertTrue(self.log.verify()["ok"])
            reloaded = audit_module.AuditLog(self.directory / "audit.jsonl", self.directory / "audit.anchor")
            self.assertTrue(reloaded.verify()["ok"])

    def test_values_are_sanitised_and_bounded(self):
        entry = self.log.record("a\nb", "n" * 200, "x", "d" * 2000)
        self.assertEqual((entry["actor"], len(entry["node"]), len(entry["detail"])), ("ab", 64, 512))

    def test_file_is_private(self):
        self.log.record("admin", "n", "x")
        import os
        import stat
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(os.stat(self.directory / "audit.jsonl").st_mode), 0o600)


class ReplayGuardTest(unittest.TestCase):
    def test_nonce_is_single_use_per_node(self):
        from agenti.nodes.deviceauth import ReplayGuard
        guard, now = ReplayGuard(), time.time()
        self.assertTrue(guard.accept("pc-uno", "n" * 20, now))
        self.assertFalse(guard.accept("pc-uno", "n" * 20, now + 1))
        self.assertTrue(guard.accept("pc-due", "n" * 20, now))
        self.assertTrue(guard.accept("pc-uno", "n" * 20, now + 1000))

    def test_cache_is_bounded(self):
        from agenti.nodes import deviceauth
        guard, now = deviceauth.ReplayGuard(), time.time()
        with mock.patch.object(deviceauth, "MAX_NONCES", 10):
            results = [guard.accept("pc-uno", f"{i:020d}", now) for i in range(15)]
        self.assertEqual(results.count(False), 5)
