import unittest
from unittest import mock

from agenti.governor.service import Governor
from agenti.team import swarm as swarm_module
from agenti.team.scanner import scanner
from agenti.team.swarm import Swarm

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustSwarm") and hasattr(nuxiva_native.RustSwarm, "set_pressure")


class FakeGovernor(Governor):
    def __init__(self, value: float, high: bool, enter: float = 75.0):
        self._enter = enter
        self.pressure = mock.Mock(high=high)
        self.value = value

    def enter_level(self) -> float:
        return self._enter


class PressureRankTest(unittest.TestCase):
    def rank_for(self, value: float, high: bool) -> int:
        seen = []
        with mock.patch.object(swarm_module.swarm, "apply_pressure", side_effect=seen.append):
            FakeGovernor(value, high)._shape_swarm(value)
        return seen[-1]

    def test_levels_follow_the_governor_pressure(self):
        self.assertEqual(self.rank_for(10, False), 0)
        self.assertEqual(self.rank_for(60, False), 1)
        self.assertEqual(self.rank_for(80, True), 2)
        self.assertEqual(self.rank_for(99, True), 3)


@unittest.skipUnless(NATIVE, "modulo nativo non disponibile")
class SwarmPressureTest(unittest.TestCase):
    def setUp(self):
        self.agents = scanner.scan()
        self.swarm = Swarm()

    def test_pressure_is_clamped_remembered_and_applied_to_a_new_engine(self):
        self.swarm.apply_pressure(99)
        self.assertEqual(self.swarm.pressure, 3)
        self.swarm.apply_pressure(-4)
        self.assertEqual(self.swarm.pressure, 0)
        self.swarm.apply_pressure(2)
        engine = self.swarm._engine_for(self.agents)
        self.assertEqual(engine.pressure(), 2)
        self.swarm.apply_pressure(1)
        self.assertEqual(engine.pressure(), 1)

    def test_engine_pressure_is_bounded_by_the_core(self):
        engine = self.swarm._engine_for(self.agents)
        engine.set_pressure(200)
        self.assertEqual(engine.pressure(), 3)
