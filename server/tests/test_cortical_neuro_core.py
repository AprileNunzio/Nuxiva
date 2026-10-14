import unittest

from server.core.kernel.domain.limbic_state import LimbicState
from server.core.kernel.domain.node import SpikingNeuronNode, SynapticSpike
from server.core.kernel.swarm.cortical_workspace import CorticalGlobalWorkspace, ThoughtOutcome
from server.features.cognitive_triage_agents.interfaces import UserCognitiveInput
from server.features.cognitive_triage_agents.psychological_agent import PsychologicalAgent
from server.features.human_affective_engine.affective_fusion_engine import affective_fusion_engine
from server.features.human_affective_engine.interfaces import (
    HeartRateMetrics,
    OcularGazeBiomarkers,
    PhysiologicalMultimodalPayload,
    VoiceAcousticBiomarkers,
)


class CorticalNeuroCoreTest(unittest.IsolatedAsyncioTestCase):
    def test_limbic_state_decay_and_excitation(self):
        limbic = LimbicState(dopamine=0.9, noradrenaline=0.8, serotonin=0.2, cortisol=0.7)
        limbic.apply_homeostatic_decay(current_ts=limbic.last_update_ts + 60.0)
        self.assertLess(limbic.noradrenaline, 0.8)
        self.assertLess(limbic.cortisol, 0.7)
        self.assertGreater(limbic.serotonin, 0.2)

        limbic.excite_emergency(0.5)
        self.assertGreater(limbic.noradrenaline, 0.3)
        self.assertGreater(limbic.cortisol, 0.2)

        vth = limbic.modulate_firing_threshold(1.0)
        self.assertLess(vth, 1.0)

        lanes = limbic.modulate_parallel_lanes(4)
        self.assertGreaterEqual(lanes, 4)
        self.assertLessEqual(lanes, 8)

    async def test_spiking_neuron_lif_integration(self):
        limbic = LimbicState()
        neuron = SpikingNeuronNode(node_id="test_neuron", threshold=0.8)
        neuron.set_weight("source_a", 0.9)

        weak_spike = SynapticSpike(
            source_neuron="source_a",
            target_cluster="test_cluster",
            potential=0.3,
        )
        fired = await neuron.integrate_and_fire(weak_spike, limbic)
        self.assertEqual(len(fired), 0)
        self.assertGreater(neuron.potential, 0.0)

        strong_spike = SynapticSpike(
            source_neuron="source_a",
            target_cluster="test_cluster",
            potential=0.9,
        )
        fired2 = await neuron.integrate_and_fire(strong_spike, limbic)
        self.assertEqual(len(fired2), 1)
        self.assertEqual(fired2[0].source_neuron, "test_neuron")
        self.assertEqual(neuron.potential, neuron.reset_potential)

    async def test_cortical_global_workspace_ignition(self):
        limbic = LimbicState(dopamine=0.8, noradrenaline=0.2, serotonin=0.5, cortisol=0.1)
        workspace = CorticalGlobalWorkspace(synaptic_bus=None, limbic=limbic)

        workspace.pre_activate_sublexical(["memory_recall", "logic_dag"])
        self.assertGreater(workspace.neurons["memory_recall"].potential, 0.3)

        spikes = [
            SynapticSpike(
                source_neuron="sensory_talamus",
                target_cluster="logic_dag",
                potential=0.95,
                payload="winning_hypothesis_a",
            ),
            SynapticSpike(
                source_neuron="sensory_talamus",
                target_cluster="memory_recall",
                potential=0.4,
                payload="secondary_memory_b",
            ),
        ]

        outcome: ThoughtOutcome = await workspace.process_sensory_wave(spikes, timeout_s=0.2)
        self.assertTrue(outcome.ignited)
        self.assertEqual(outcome.selected_thought, "winning_hypothesis_a")
        self.assertTrue(outcome.consensus_passed)

    def test_affective_engine_limbic_closed_loop(self):
        payload = PhysiologicalMultimodalPayload(
            user_id="user_test",
            timestamp=1000.0,
            heart_metrics=HeartRateMetrics(bpm=102.0, hrv_rmssd_ms=18.0, signal_quality=0.9, pulse_confidence=0.9),
            vocal_metrics=VoiceAcousticBiomarkers(
                pitch_f0_mean_hz=160.0,
                pitch_variability_st=30.0,
                jitter_percent=3.2,
                shimmer_percent=1.5,
                monotone_score=0.2,
                vocal_energy_rms=0.5,
                speech_pause_ratio=0.1,
                depressive_vocal_indicator=0.2,
            ),
            ocular_metrics=OcularGazeBiomarkers(
                gaze_direction="center",
                downward_gaze_ratio=0.02,
                blink_rate_per_min=32.0,
                eye_aspect_ratio_mean=0.3,
                fixation_stagnation_score=0.1,
                blunted_affect_indicator=0.1,
            ),
        )
        limbic = affective_fusion_engine.compute_limbic_update(payload)
        self.assertGreater(limbic.noradrenaline, 0.4)
        self.assertGreater(limbic.cortisol, 0.3)

    def test_theory_of_mind_discrepancy(self):
        agent = PsychologicalAgent()
        discrepant_input = UserCognitiveInput(
            user_id="user_test",
            raw_text="Sto bene, tutto ok nessun problema",
            vocal_jitter=0.05,
            facial_valence=-0.4,
            heart_rate_bpm=110.0,
            hrv_ms=20.0,
        )
        spike = agent.detect_tom_discrepancy(discrepant_input)
        self.assertIsNotNone(spike)
        self.assertEqual(spike.source_neuron, "psychological_agent")
        self.assertEqual(spike.target_cluster, "theory_of_mind")
        self.assertGreater(spike.potential, 0.9)


if __name__ == "__main__":
    unittest.main()
