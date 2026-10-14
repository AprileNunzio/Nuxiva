import unittest
from unittest.mock import patch

from features.brain import brains as brains_module
from features.brain import presets
from features.brain.components import SpikingNeuronNode, SynapticSpike
from features.people import people
from nuxiva_bus import NuxivaBus


class ReasoningModesTest(unittest.IsolatedAsyncioTestCase):
    def test_default_preset_is_neuro_core(self):
        self.assertEqual(presets.DEFAULT_PRESET_ID, "neuro_core")
        self.assertIn("neuro_core", presets.BY_ID)
        self.assertEqual(presets.clean_profile(None, False), "neuro_core")

    def test_presets_order_has_neuro_core_first(self):
        self.assertEqual(presets.PRESETS[0].id, "neuro_core")
        self.assertEqual(presets.PRESETS[0].label, "Nuxiva Neuro-Core 5.0")

    def test_commercial_reasoning_modes(self):
        self.assertEqual(len(presets.REASONING_MODES), 2)
        fast = presets.REASONING_MODES_BY_ID["fast"]
        reasoning = presets.REASONING_MODES_BY_ID["reasoning"]

        self.assertEqual(fast.name, "Nuxiva 5.0 Veloce")
        self.assertEqual(fast.version, "5.0-flash")
        self.assertEqual(fast.badge, "Veloce")

        self.assertEqual(reasoning.name, "Nuxiva 5.0 Pro Ragionamento")
        self.assertEqual(reasoning.version, "5.0-pro")
        self.assertEqual(reasoning.badge, "Ragionamento")
        self.assertTrue(reasoning.is_default)

    def test_permanent_user_preference_storage(self):
        test_slug = "test-user-reasoning"
        people.ensure(test_slug, "Test User")

        mode = people.preferred_reasoning_mode(test_slug)
        self.assertEqual(mode, "reasoning")

        saved = people.set_preferred_reasoning_mode(test_slug, "fast")
        self.assertEqual(saved, "fast")
        self.assertEqual(people.preferred_reasoning_mode(test_slug), "fast")

        saved_pro = people.set_preferred_reasoning_mode(test_slug, "5.0-pro")
        self.assertEqual(saved_pro, "reasoning")
        self.assertEqual(people.preferred_reasoning_mode(test_slug), "reasoning")

    async def test_brain_route_with_mode_override(self):
        b = brains_module.Brains()
        with patch.object(b, "installed", return_value=["granite3.3:2b", "qwen2.5:1.5b"]):
            fast_route = await b.route("dimostrami questo teorema matematico complesso", mode_override="fast")
            self.assertEqual(fast_route["kind"], "chat")

            deep_route = await b.route("ciao", mode_override="reasoning")
            self.assertEqual(deep_route["kind"], "deep")

    async def test_components_spiking_neuron_lif(self):
        neuron = SpikingNeuronNode("cortex_unit", threshold=0.7)
        neuron.set_weight("sensory_in", 0.8)

        spike = SynapticSpike("sensory_in", "cortex_unit", potential=0.2)
        fired = await neuron.integrate_and_fire(spike, None)
        self.assertEqual(len(fired), 0)

        spike_strong = SynapticSpike("sensory_in", "cortex_unit", potential=0.9)
        fired2 = await neuron.integrate_and_fire(spike_strong, None)
        self.assertEqual(len(fired2), 1)
        self.assertEqual(fired2[0].source_neuron, "cortex_unit")

    def test_nuxiva_bus_synaptic_spikes_and_stdp(self):
        bus = NuxivaBus()
        spike = bus.publish_spike("talamo", "cortex", potential=0.85, emotion_vector=[0.5, 0.2, 0.6, 0.1])
        self.assertEqual(spike.source_neuron, "talamo")
        self.assertEqual(spike.potential, 0.85)

        popped = bus.pop_spike()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.source_neuron, "talamo")

        w_initial = bus.synaptic_weights.get("talamo", "cortex")
        w_potentiated = bus.synaptic_weights.apply_stdp("talamo", "cortex", delta_t_ms=10.0, dopamine=0.8, is_reward=True)
        self.assertGreater(w_potentiated, w_initial)


if __name__ == "__main__":
    unittest.main()
