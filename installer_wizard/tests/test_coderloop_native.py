import json
import unittest

from agenti.devstudio import coderloop

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustCoderLoop")
GOOD = [coderloop.check("test", True), coderloop.check("lint", True), coderloop.check("security", True)]


def files_ok(feedback, iteration):
    return {"src/app.py": f"print({iteration})".encode()}


class Common:
    def loop(self):
        raise NotImplementedError

    def test_passes_on_second_iteration_with_untrusted_feedback(self):
        seen = []

        def files(feedback, iteration):
            seen.append(feedback)
            return files_ok(feedback, iteration)

        def checks(_files, iteration):
            if iteration == 1:
                return [coderloop.check("test", False, "assertion failed\npassword = hunter2"), coderloop.check("lint", True), coderloop.check("security", True)], "run-1"
            return GOOD, "run-2"

        result = coderloop.run_task(files, checks, self.loop())
        self.assertEqual(result["outcome"]["outcome"], "passed")
        self.assertEqual(result["outcome"]["iterations"], 2)
        self.assertIsNone(seen[0])
        self.assertNotIn("hunter2", seen[1]["untrusted_log"])
        self.assertTrue(all(line.startswith("| ") for line in seen[1]["untrusted_log"].splitlines()))

    def test_push_requires_passed_permit(self):
        loop = self.loop()
        result = coderloop.run_task(files_ok, lambda f, i: (GOOD, "run-1"), loop)
        digest = result["outcome"]["artifact"]["digest"]
        self.assertEqual(loop.authorize(digest, '{"kind":"local"}', False), "allowed")
        self.assertEqual(loop.authorize(digest, '{"kind":"remote","repo":"me/other"}', False), "needs_consent")
        self.assertEqual(loop.authorize(digest, '{"kind":"remote","repo":"me/other"}', True), "allowed")
        self.assertEqual(loop.authorize("0" * 64, '{"kind":"local"}', True), "denied")
        loop.revoke(digest)
        self.assertEqual(loop.authorize(digest, '{"kind":"local"}', True), "denied")

    def test_failed_loop_issues_no_permit(self):
        loop = self.loop()
        result = coderloop.run_task(files_ok, lambda f, i: ([coderloop.check("test", False, f"boom {i}")], "run-1"), loop)
        self.assertNotEqual(result["outcome"]["outcome"], "passed")
        self.assertEqual(loop.authorize("0" * 64, '{"kind":"local"}', True), "denied")

    def test_protected_paths_are_a_policy_violation(self):
        for path in ("critic/rules.toml", "../x", "/abs", ".github/workflows/ci.yml"):
            result = coderloop.run_task(lambda f, i, p=path: {p: b"x"}, lambda f, i: (GOOD, "run-1"), self.loop())
            self.assertEqual(result["outcome"]["reason"], "policy_violation", path)

    def test_critic_cannot_vouch_for_failed_checks(self):
        result = coderloop.run_task(files_ok, lambda f, i: ([coderloop.check("test", False), coderloop.check("lint", True), coderloop.check("security", True)], "run-1"), self.loop())
        self.assertNotEqual(result["outcome"]["outcome"], "passed")

    def test_same_artifact_digest_on_both_engines(self):
        result = coderloop.run_task(files_ok, lambda f, i: (GOOD, "run-1"), self.loop())
        self.assertEqual(len(result["outcome"]["artifact"]["digest"]), 64)


class PythonFallbackTest(Common, unittest.TestCase):
    def loop(self):
        return coderloop.PyLoop()


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeTest(Common, unittest.TestCase):
    def loop(self):
        return nuxiva_native.RustCoderLoop()

    def test_digest_parity_with_python_fallback(self):
        native = coderloop.run_task(files_ok, lambda f, i: (GOOD, "run-1"), self.loop())["outcome"]["artifact"]["digest"]
        python = coderloop.run_task(files_ok, lambda f, i: (GOOD, "run-1"), coderloop.PyLoop())["outcome"]["artifact"]["digest"]
        self.assertEqual(native, python)

    def test_unknown_settings_are_refused(self):
        with self.assertRaises(ValueError):
            nuxiva_native.RustCoderLoop('{"bogus": 1}')

    def test_remote_repo_declared_autonomous_needs_no_consent(self):
        settings = json.loads(json.dumps({"max_iterations": 5, "repeat_escalate": 2, "inconclusive_max": 2, "log_chars": 4000, "max_files": 256,
                                          "required_checks": ["test", "lint", "security"], "protected_prefixes": ["critic/"],
                                          "autonomous_repos": ["me/free"], "audit_cap": 100}))
        loop = nuxiva_native.RustCoderLoop(json.dumps(settings))
        digest = coderloop.run_task(files_ok, lambda f, i: (GOOD, "run-1"), loop)["outcome"]["artifact"]["digest"]
        self.assertEqual(loop.authorize(digest, '{"kind":"remote","repo":"me/free"}', False), "allowed")
        self.assertEqual(len(json.loads(loop.audit())), 1)

    def test_hostile_authorize_input_is_refused(self):
        with self.assertRaises(ValueError):
            self.loop().authorize("a" * 64, "not json", True)


if __name__ == "__main__":
    unittest.main()
