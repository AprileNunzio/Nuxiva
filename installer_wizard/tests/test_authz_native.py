import itertools
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
from agenti.authz import policy as policy_module
from agenti.authz import risk
from agenti.authz.principal import Principal, Strength
from agenti.authz.risk import Risk

NATIVE = native_core.load()
READY = NATIVE is not None and hasattr(NATIVE, "RustAuthzPolicy") and hasattr(NATIVE, "RustRiskTable")
ROLES = list(policy_module.DEFAULT_CEILING) + ["stranger"]
SUBROLES = ["", "butler", "nanny", "cleaner", "ghost"]
OVERRIDES = ["", "info", " Files ", "CRITICAL", "bogus"]
POLICIES = [{}, {"ceiling": {"guest": "personal", "system": "info", "family": "bogus", "ghost": "files"}},
            {"proof": {"critical": "weak", "personal": "none", "home": "strong", "files": "STRONG", "info": "single"}},
            {"ceiling": {"anonymous": "info", "staff": "critical"}, "proof": {"files": 3, "personal": "single"}},
            {"ceiling": None, "proof": None}]


def fresh():
    with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(policy_module, "POLICY_FILE", Path(tmp) / "policy.json"):
        return policy_module.Policy()


@unittest.skipUnless(READY, "modulo nativo authz-core non installato")
class AuthzParityTest(unittest.TestCase):

    def test_decisions_match_for_every_combination(self):
        for data in POLICIES:
            engine = fresh()
            self.assertIsNotNone(engine.engine)
            engine.apply(data)
            reference = fresh()
            reference._py_apply(data)
            with self.subTest(policy=data):
                self.assertEqual(engine.export(), reference.export())
            for role, subrole, override, strength, level in itertools.product(
                    ROLES, SUBROLES, OVERRIDES, list(Strength), list(Risk)):
                who = Principal(slug="x", role=role, subrole=subrole, override=override, strength=strength)
                with self.subTest(policy=data, role=role, subrole=subrole, override=override,
                                  strength=strength, risk=level):
                    self.assertEqual(engine.limit(who), reference._py_limit(who))
                    self.assertEqual(engine.check(who, level), reference._py_check(who, level))

    def test_tool_risks_match(self):
        risk.compose("t_morning", ["now", "read_file"])
        risk.compose("t_loop_a", ["t_loop_b"])
        risk.compose("t_loop_b", ["t_loop_a"])
        risk.compose("t_nested", ["t_morning", "send_email"])
        risk.compose("t_empty", [])
        try:
            names = sorted(risk.TOOLS) + ["t_morning", "t_loop_a", "t_nested", "t_empty", "unknown_tool"]
            for name in names:
                with self.subTest(tool=name):
                    self.assertEqual(risk.of_tool(name), risk._py_of_tool(name))
            risk.forget("t_morning")
            self.assertEqual(risk.of_tool("t_morning"), Risk.CRITICAL)
            self.assertEqual(risk.of_tool("t_nested"), risk._py_of_tool("t_nested"))
        finally:
            for name in ("t_morning", "t_loop_a", "t_loop_b", "t_nested", "t_empty"):
                risk.forget(name)


class AuthzFallbackTest(unittest.TestCase):

    def test_python_engine_still_decides(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            engine = fresh()
            self.assertIsNone(engine.engine)
            owner = Principal(slug="o", role="owner", strength=Strength.STRONG)
            guest = Principal(slug="g", role="guest", strength=Strength.STRONG)
            self.assertTrue(engine.check(owner, Risk.CRITICAL).allowed)
            self.assertEqual(engine.check(guest, Risk.PERSONAL).code, "role")


if __name__ == "__main__":
    unittest.main()
