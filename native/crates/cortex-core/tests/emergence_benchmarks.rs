use nuxiva_cortex_core::{
    BasalGangliaGating, BayesianTheoryOfMindEngine, CandidateAction, CausalGraph,
    CerebellarForwardModel, ConditionalProbabilityTable, GlobalWorkspace,
    JustificationTruthMaintenanceSystem, OntogeneticBootstrapEngine, SallyAnneQuery,
    SymbolGroundingEngine, ThalamicRelay, TriSynapticHippocampus, UniversalActiveInferenceEngine,
    WorkspaceHypothesis,
};

#[test]
fn test_benchmark_1_sensorimotor_causal_metacognitive_synergy() {
    let mut cerebellum = CerebellarForwardModel::new(3, 4, 3);
    let mut active_inf = UniversalActiveInferenceEngine::new(3, 3, 3);
    let mut causal = CausalGraph::new();
    let mut jtms = JustificationTruthMaintenanceSystem::new();
    let basal_ganglia = BasalGangliaGating::default();

    causal.add_node("actuator_healthy");
    causal.add_node("motor_execution_nominal");
    causal.add_directed_edge("actuator_healthy", "motor_execution_nominal");
    let mut cpt = ConditionalProbabilityTable::new(
        "motor_execution_nominal",
        vec!["actuator_healthy".to_string()],
    );
    cpt.set_prob("actuator_healthy_1", 0.98);
    cpt.set_prob("actuator_healthy_0", 0.05);
    causal.set_cpt(cpt);

    jtms.assert_fact("fact_actuator_operational", "actuator_healthy=true", 1000.0);
    jtms.assert_justified(
        "belief_high_precision_grasp",
        "capability=grasp",
        "rule_nominal_actuation",
        vec!["fact_actuator_operational".to_string()],
        1000.0,
    );
    assert!(jtms.is_belief_valid("belief_high_precision_grasp"));

    let state = vec![0.5, 0.2, -0.1];
    let degraded_observed = vec![-0.6, 0.3, -0.2];

    let climbing_error = cerebellum.learn_climbing_fiber_error(&state, &degraded_observed);
    let vfe = active_inf.update_variational_free_energy(&degraded_observed);

    assert!(climbing_error > 0.3);
    assert!(vfe > 0.1);

    let p_nominal_degraded = causal.observe("motor_execution_nominal", "actuator_healthy", false);
    assert!(p_nominal_degraded < 0.10);

    let retracted = jtms.retract(
        "fact_actuator_operational",
        "climbing_fiber_divergence",
        1050.0,
    );
    assert!(retracted.contains(&"belief_high_precision_grasp".to_string()));
    assert!(!jtms.is_belief_valid("belief_high_precision_grasp"));

    let candidates = vec![
        CandidateAction {
            id: "aggressive_rapid_thrust".to_string(),
            expected_reward: 0.9,
            risk_estimate: 0.95,
            payload: vec![1.0],
        },
        CandidateAction {
            id: "cautious_slow_adaptation".to_string(),
            expected_reward: 0.6,
            risk_estimate: 0.1,
            payload: vec![0.2],
        },
    ];

    let decision = basal_ganglia.select_action(&candidates, -0.5);
    assert_eq!(
        decision.selected_action.map(|a| a.id),
        Some("cautious_slow_adaptation".to_string())
    );
}

#[test]
fn test_benchmark_2_sally_anne_false_belief_and_social_tom() {
    let mut tom = BayesianTheoryOfMindEngine::new();
    let mut hippocampus = TriSynapticHippocampus::new(8, 32, 1.0);

    tom.register_agent("agent_sally", 1);
    tom.register_agent("agent_anne", 1);

    tom.update_agent_observation("agent_sally", "red_ball", "basket");
    tom.update_agent_observation("agent_anne", "red_ball", "basket");

    hippocampus.encode_and_store_episode(
        "ep_init",
        100.0,
        vec![0.1; 8],
        "sally_places_ball",
        "ball_in_basket",
        0.0,
    );

    tom.notify_world_change("red_ball", "box", &["agent_anne"]);
    hippocampus.encode_and_store_episode(
        "ep_moved",
        200.0,
        vec![0.8; 8],
        "anne_moves_ball",
        "ball_in_box",
        0.9,
    );

    let query_sally = SallyAnneQuery {
        object_name: "red_ball".to_string(),
        true_current_location: "box".to_string(),
        observer_agent_id: "agent_sally".to_string(),
    };
    let sally_res = tom.solve_sally_anne(&query_sally);
    assert_eq!(sally_res.predicted_search_location, "basket");
    assert!(sally_res.holds_false_belief);

    let query_anne = SallyAnneQuery {
        object_name: "red_ball".to_string(),
        true_current_location: "box".to_string(),
        observer_agent_id: "agent_anne".to_string(),
    };
    let anne_res = tom.solve_sally_anne(&query_anne);
    assert_eq!(anne_res.predicted_search_location, "box");
    assert!(!anne_res.holds_false_belief);

    let direct_memory_query = SallyAnneQuery {
        object_name: "red_ball".to_string(),
        true_current_location: "box".to_string(),
        observer_agent_id: "absent_lesioned_agent".to_string(),
    };
    let fallback_res = tom.solve_sally_anne(&direct_memory_query);
    assert_eq!(fallback_res.predicted_search_location, "box");
    assert!(!fallback_res.holds_false_belief);
}

#[test]
fn test_benchmark_3_ontogenetic_tabula_rasa_run() {
    let mut dev = OntogeneticBootstrapEngine::default();
    let mut grounder = SymbolGroundingEngine::new(0.5);
    let mut active_inf = UniversalActiveInferenceEngine::new(2, 2, 2);

    let mut vfe_history = Vec::new();

    for tick in 0..160i32 {
        let decay = 1.0 / (1.0 + f64::from(tick) * 0.05);
        let sign = if tick % 2 == 0 { 1.0 } else { -1.0 };
        let sensorimotor_stimulus = vec![sign * 1.5 * decay, -sign * 1.5 * decay];
        let vfe = active_inf.update_variational_free_energy(&sensorimotor_stimulus);
        vfe_history.push(vfe);

        grounder.ground_observation(&sensorimotor_stimulus, "percept_stream");
        dev.tick(vfe.min(1.0));
    }

    assert!(grounder.symbol_count() > 1);
    assert_eq!(dev.stage_description(), "symbol_grounding_and_concepts");

    let early_chunk = vfe_history.get(0..20).unwrap_or(&[]);
    let late_chunk = vfe_history.get(140..160).unwrap_or(&[]);
    let early_vfe_mean = early_chunk.iter().sum::<f64>() / 20.0;
    let late_vfe_mean = late_chunk.iter().sum::<f64>() / 20.0;
    assert!(late_vfe_mean <= early_vfe_mean);
}

#[test]
fn test_benchmark_4_neuropsychological_ablation_matrix() {
    struct CognitiveArchitecture {
        basal_ganglia: Option<BasalGangliaGating>,
        cerebellum: Option<CerebellarForwardModel>,
        thalamus: Option<ThalamicRelay>,
        workspace: Option<GlobalWorkspace>,
    }

    impl CognitiveArchitecture {
        fn evaluate_full_performance(&mut self) -> f64 {
            let mut score = 0.0;

            if let Some(bg) = &self.basal_ganglia {
                let cand = vec![CandidateAction {
                    id: "act_1".to_string(),
                    expected_reward: 0.8,
                    risk_estimate: 0.2,
                    payload: vec![1.0],
                }];
                if bg.select_action(&cand, 0.5).selected_action.is_some() {
                    score += 0.25;
                }
            }

            if let Some(cb) = &mut self.cerebellum {
                let err = cb.learn_climbing_fiber_error(&[0.1, 0.2, 0.3], &[0.1, 0.2, 0.3]);
                if err.is_finite() {
                    score += 0.25;
                }
            }

            if let Some(th) = &self.thalamus {
                let gated = th.gate_signal("sensory_vision", &[1.0, 2.0]);
                if !gated.is_empty() {
                    score += 0.25;
                }
            }

            if let Some(gw) = &mut self.workspace {
                let hyp = vec![WorkspaceHypothesis {
                    source_module: "columns".to_string(),
                    content_summary: "theorem_proved".to_string(),
                    saliency_weight: 0.9,
                    precision_confidence: 0.9,
                    vector_payload: vec![1.0],
                }];
                if gw.compete_and_ignite(&hyp).is_some() {
                    score += 0.25;
                }
            }

            score
        }
    }

    let mut full = CognitiveArchitecture {
        basal_ganglia: Some(BasalGangliaGating::default()),
        cerebellum: Some(CerebellarForwardModel::new(3, 2, 3)),
        thalamus: Some(ThalamicRelay::default()),
        workspace: Some(GlobalWorkspace::default()),
    };
    let full_score = full.evaluate_full_performance();
    assert!((full_score - 1.0).abs() < 1e-6);

    let mut lesioned_bg = CognitiveArchitecture {
        basal_ganglia: None,
        cerebellum: Some(CerebellarForwardModel::new(3, 2, 3)),
        thalamus: Some(ThalamicRelay::default()),
        workspace: Some(GlobalWorkspace::default()),
    };
    let score_no_bg = lesioned_bg.evaluate_full_performance();
    assert!((score_no_bg - 0.75).abs() < 1e-6);

    let mut lesioned_cerebellum = CognitiveArchitecture {
        basal_ganglia: Some(BasalGangliaGating::default()),
        cerebellum: None,
        thalamus: Some(ThalamicRelay::default()),
        workspace: Some(GlobalWorkspace::default()),
    };
    let score_no_cb = lesioned_cerebellum.evaluate_full_performance();
    assert!((score_no_cb - 0.75).abs() < 1e-6);

    let phi_emergence = full_score - 0.75;
    assert!(phi_emergence > 0.15);
}
