import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from features.brain import brains as brains_module
from features.brain import presets
from features.brain.assignments import load_synaptic_weights, save_synaptic_weights
from features.brain.components import LimbicModulator, SpikingNeuron, SpikingNeuronNode, SynapticSpike
from features.chat.brain_chain import CorticalBrainChain, cortical_chain
from features.mind.scoring import compute_emotional_salience, score_memory_retention
from features.people import people
from features.scene.fusion import PresenceFusion
from features.twin.simulator import predict_user_impact
from features.vision.nightly import consolidate_synapses
from loops import DefaultModeNetwork
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

    def test_limbic_modulator_biometrics_and_threshold(self):
        limbic = LimbicModulator()
        base_thresh = limbic.compute_threshold(0.7)
        limbic.ingest_biometrics(vocal_stress=0.8, facial_valence=-0.5, heart_rate_delta=0.4, system_pressure=0.7)
        stressed_thresh = limbic.compute_threshold(0.7)
        self.assertNotEqual(base_thresh, stressed_thresh)
        self.assertLessEqual(limbic.parallel_branch_budget(8), 8)

    async def test_spiking_neuron_stdp_and_firing(self):
        neuron = SpikingNeuron("pyramidal_1", role="deep", base_threshold=0.5)
        neuron.connect("motor_1", weight=0.8)
        spike = SynapticSpike(source_id="sensory_1", target_id="pyramidal_1", potential=0.7)
        p = neuron.integrate(spike)
        self.assertGreater(p, 0.0)

        fired = await neuron.evaluate_and_fire({"thought": "analyze"}, LimbicModulator())
        self.assertGreaterEqual(len(fired), 1)

        w = neuron.apply_stdp("motor_1", post_fired_at=neuron.last_fired_at + 0.01, reward_signal=1.2)
        self.assertGreater(w, 0.8)

    async def test_cortical_brain_chain_parallel_thought(self):
        chain = CorticalBrainChain()
        chain.set_mode("nuxiva-5.0-fast")

        async def branch_slow(q, ctx, limbic):
            await asyncio.sleep(0.05)
            return {"text": "slow result", "confidence": 0.5}

        async def branch_fast(q, ctx, limbic):
            return {"text": "fast ignited result", "confidence": 0.95}

        res = await chain.execute_parallel_thought(
            "calcola il teorema",
            {},
            [branch_slow, branch_fast],
            critic_fn=predict_user_impact,
        )
        self.assertIn("fast ignited result", res.get("text", ""))
        self.assertIn("limbic_snapshot", res)

    def test_emotional_salience_and_retention(self):
        s_neutral = compute_emotional_salience(valence=0.0, arousal=0.1)
        s_intense = compute_emotional_salience(valence=0.9, arousal=0.8, dopamine=0.9, noradrenaline=0.8)
        self.assertGreater(s_intense, s_neutral)

        now = 100000.0
        mem = {"timestamp": now - 3600.0, "importance": 0.8, "rehearsals": 2, "limbic": {"valence": 0.8, "arousal": 0.7}}
        score = score_memory_retention(mem, query_similarity=0.9, now_ts=now)
        self.assertGreater(score, 0.5)

    def test_synaptic_weights_persistence(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            p = Path(tf.name)
        save_synaptic_weights({"conversation:qwen2.5:1.5b": 1.25}, file_path=p)
        loaded = load_synaptic_weights(file_path=p)
        p.unlink(missing_ok=True)
        self.assertEqual(loaded.get("conversation:qwen2.5:1.5b"), 1.25)

    def test_sensory_limbic_biometrics_binding(self):
        fusion = PresenceFusion(publish=lambda t, p, r=False: None)
        fusion.add("user_test", "face", 0.9, "User Test")
        snapshot = fusion.step()
        self.assertGreaterEqual(len(snapshot["people"]), 1)
        self.assertGreater(cortical_chain.limbic.valence, -1.0)

    async def test_default_mode_network_idle_cycle(self):
        dmn = DefaultModeNetwork(idle_threshold_s=0.01)
        dmn.last_interaction = 0.0
        await dmn._cycle()
        self.assertGreaterEqual(dmn.last_dmn_run, 0.0)

    def test_rem_synaptic_consolidation(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            p = Path(tf.name)
        save_synaptic_weights({"analytic_reasoner:qwen2.5:14b": 1.4}, file_path=p)
        with patch("features.brain.assignments.load_synaptic_weights", return_value={"analytic_reasoner:qwen2.5:14b": 1.4}), \
             patch("features.brain.assignments.save_synaptic_weights") as mock_save:
            res = consolidate_synapses()
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["count"], 1)
            mock_save.assert_called_once()
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
