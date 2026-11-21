use agency_domain::TaskSpec;
use agency_planner::TaskGraph;

use crate::{
    ArchitectureCandidate, ContractKind, ContractRegistry, EvaluationWeights, InquiryScope,
    InterfaceContract, ResolutionSource, SubTaskBlueprint, evaluate_candidates, expand_task_node,
    interrogate_goal, recruit_specialists,
};

#[test]
fn tree_of_thoughts_selects_highest_scoring_architecture() {
    let candidates = vec![
        ArchitectureCandidate {
            id: "monolith-legacy".to_owned(),
            title: "Monolite Legacy".to_owned(),
            summary: "Singolo file non modulare".to_owned(),
            stack: vec!["python".to_owned()],
            scalability: 45,
            security: 50,
            maintainability: 40,
            velocity: 75,
            cost_efficiency: 70,
            risk_penalty: 35,
        },
        ArchitectureCandidate {
            id: "modular-rust-web".to_owned(),
            title: "Architettura Modulare Rust + React".to_owned(),
            summary: "Micro-moduli zero-trust con backend Tokio e UI reattiva".to_owned(),
            stack: vec![
                "rust".to_owned(),
                "tokio".to_owned(),
                "postgres".to_owned(),
                "react".to_owned(),
                "stripe".to_owned(),
                "docker".to_owned(),
            ],
            scalability: 95,
            security: 96,
            maintainability: 92,
            velocity: 85,
            cost_efficiency: 90,
            risk_penalty: 5,
        },
    ];

    let res = evaluate_candidates(&candidates, EvaluationWeights::default());
    assert!(res.is_ok());
    if let Ok(verdict) = res {
        assert_eq!(verdict.selected_id, "modular-rust-web");
        assert!(verdict.selected_score_bps > 8_000);
        assert!(
            verdict
                .required_specialists
                .contains(&"architect".to_owned())
        );
        assert!(verdict.required_specialists.contains(&"backend".to_owned()));
        assert!(
            verdict
                .required_specialists
                .contains(&"frontend".to_owned())
        );
        assert!(
            verdict
                .required_specialists
                .contains(&"security".to_owned())
        );
        assert!(verdict.required_specialists.contains(&"devops".to_owned()));
        assert!(verdict.required_specialists.contains(&"qa".to_owned()));
    }
}

#[test]
fn socratic_interrogation_escalates_unspecified_payment_and_resolves_rest() {
    let report = interrogate_goal(
        "Creami un progetto di un sito e-commerce di informatica",
        &[],
    );
    assert!(report.is_ok());
    if let Ok(r) = report {
        assert_eq!(r.user_escalations.len(), 1);
        if let Some(esc) = r.user_escalations.first() {
            assert_eq!(esc.id, "q-payment-gateway");
            assert_eq!(esc.scope, InquiryScope::PaymentAndCompliance);
            assert_eq!(esc.resolution, ResolutionSource::EscalateToUser);
        }
        assert!(r.autonomous_decisions.len() >= 3);
        assert!(r.invariants.len() >= 4);
    }

    let resolved = interrogate_goal(
        "Creami un sito e-commerce di informatica con Stripe e PostgreSQL",
        &[],
    );
    assert!(resolved.is_ok());
    if let Ok(r2) = resolved {
        assert!(r2.user_escalations.is_empty());
        assert_eq!(r2.confidence_bps, 9_500);
    }
}

#[test]
fn specialist_recruitment_builds_domain_specific_team() {
    let team = recruit_specialists(
        "Sito e-commerce di informatica con configuratore 3D e deploy Docker",
        "Rust + React + Three.js",
    );
    assert!(team.is_ok());
    if let Ok(roster) = team {
        let ids: Vec<&str> = roster.iter().map(|s| s.id.as_str()).collect();
        assert!(ids.contains(&"architect"));
        assert!(ids.contains(&"backend"));
        assert!(ids.contains(&"frontend"));
        assert!(ids.contains(&"commerce_specialist"));
        assert!(ids.contains(&"graphics_3d"));
        assert!(ids.contains(&"security"));
        assert!(ids.contains(&"qa"));
        assert!(ids.contains(&"devops"));
    }
}

#[test]
fn hierarchical_decomposition_expands_task_into_sub_dag() {
    let base_specs = vec![
        TaskSpec {
            id: "arch".to_owned(),
            title: "Architettura Sistema".to_owned(),
            role: "architect".to_owned(),
            depends_on: vec![],
            acceptance: vec!["Schema definito".to_owned()],
            estimate_seconds: 120,
            max_attempts: 3,
            budget_tokens: Some(6_000),
            budget_seconds: Some(300),
        },
        TaskSpec {
            id: "checkout".to_owned(),
            title: "Modulo Checkout".to_owned(),
            role: "backend".to_owned(),
            depends_on: vec!["arch".to_owned()],
            acceptance: vec!["Ordini completati".to_owned()],
            estimate_seconds: 600,
            max_attempts: 3,
            budget_tokens: Some(9_000),
            budget_seconds: Some(600),
        },
    ];

    let graph_res = TaskGraph::from_specs(&base_specs);
    assert!(graph_res.is_ok());
    if let Ok(mut graph) = graph_res {
        let subtasks = vec![
            SubTaskBlueprint {
                suffix: "cart_validation".to_owned(),
                title: "Validazione stock e prezzi carrello".to_owned(),
                role: "commerce_specialist".to_owned(),
                depends_on_suffixes: vec![],
                acceptance: vec!["Stock verificato".to_owned()],
                estimate_seconds: 200,
            },
            SubTaskBlueprint {
                suffix: "payment_intent".to_owned(),
                title: "Creazione PaymentIntent idempotente".to_owned(),
                role: "backend".to_owned(),
                depends_on_suffixes: vec!["cart_validation".to_owned()],
                acceptance: vec!["Webhook firmato".to_owned()],
                estimate_seconds: 250,
            },
        ];

        let exp = expand_task_node(&mut graph, "checkout", &subtasks);
        assert!(exp.is_ok());
        if let Ok(res) = exp {
            assert_eq!(res.added_tasks.len(), 2);
            assert!(
                res.added_tasks
                    .contains(&"checkout_cart_validation".to_owned())
            );
            assert!(
                res.added_tasks
                    .contains(&"checkout_payment_intent".to_owned())
            );
            assert_eq!(graph.len(), 4);
        }
    }
}

#[test]
fn contract_registry_versions_and_filters_by_role() {
    let mut reg = ContractRegistry::new();
    let contract = InterfaceContract {
        id: "api.catalog.search".to_owned(),
        kind: ContractKind::HttpEndpoint,
        producer_role: "backend".to_owned(),
        consumer_roles: vec!["frontend".to_owned(), "qa".to_owned()],
        version: 0,
        schema: "GET /api/v1/products?q=gpu -> 200 ProductList".to_owned(),
        invariants: vec!["Latenza < 50ms".to_owned()],
    };

    let v1 = reg.publish(contract.clone());
    assert!(v1.is_ok());
    if let Ok(c1) = v1 {
        assert_eq!(c1.version, 1);
    }

    let v2 = reg.publish(contract);
    assert!(v2.is_ok());
    if let Ok(c2) = v2 {
        assert_eq!(c2.version, 2);
    }

    assert_eq!(reg.for_role("frontend").len(), 1);
    assert_eq!(reg.for_role("backend").len(), 1);
    assert_eq!(reg.for_role("devops").len(), 0);
}

#[test]
fn epistemic_inquiry_schedules_self_probes_and_resolves_via_findings() {
    use crate::{EpistemicHypothesis, ProbeChannel, ProbeFinding, synthesize_epistemic_plan};

    let hypotheses = vec![
        EpistemicHypothesis {
            id: "hyp.db.engine".to_owned(),
            scope: InquiryScope::DataModel,
            question_key: "i18n.inquiry.db_engine".to_owned(),
            default_answer_key: "i18n.inquiry.db_default_sqlite".to_owned(),
            impact_on_schema: 80,
            reversibility: 40,
            probe_channel: Some(ProbeChannel::EnvironmentConfig),
            probe_query: Some("DATABASE_URL".to_owned()),
            options_keys: vec![
                "i18n.option.postgres".to_owned(),
                "i18n.option.sqlite".to_owned(),
            ],
        },
        EpistemicHypothesis {
            id: "hyp.payment.provider".to_owned(),
            scope: InquiryScope::PaymentAndCompliance,
            question_key: "i18n.inquiry.payment_gateway".to_owned(),
            default_answer_key: "i18n.inquiry.payment_stripe".to_owned(),
            impact_on_schema: 95,
            reversibility: 20,
            probe_channel: None,
            probe_query: None,
            options_keys: vec![
                "i18n.option.stripe".to_owned(),
                "i18n.option.paypal".to_owned(),
            ],
        },
    ];

    let plan_before = synthesize_epistemic_plan("Build platform", &hypotheses, &[], &[]);
    assert!(plan_before.is_ok());
    if let Ok(p1) = plan_before {
        assert_eq!(p1.self_probes.len(), 1);
        assert_eq!(p1.report.user_escalations.len(), 1);
        assert_eq!(p1.report.autonomous_decisions.len(), 1);
    }

    let findings = vec![ProbeFinding {
        hypothesis_id: "hyp.db.engine".to_owned(),
        resolved: true,
        resolved_answer_key: "i18n.inquiry.db_resolved_postgres".to_owned(),
        confidence_boost_bps: 350,
    }];

    let plan_after = synthesize_epistemic_plan("Build platform", &hypotheses, &findings, &[]);
    assert!(plan_after.is_ok());
    if let Ok(p2) = plan_after {
        assert!(p2.self_probes.is_empty());
        assert_eq!(p2.report.autonomous_decisions.len(), 1);
        if let Some(dec) = p2.report.autonomous_decisions.first() {
            assert_eq!(dec.answer, "i18n.inquiry.db_resolved_postgres");
        }
    }
}

#[test]
fn active_inference_generates_intrinsic_goals_and_applies_godel_pareto_upgrades() {
    use crate::{
        AlgorithmicStrategy, AutonomousAgiKernel, PolicyCandidate, WorldTransition,
        select_minimal_free_energy_policy,
    };

    let mut kernel = AutonomousAgiKernel::new();
    let transition = WorldTransition {
        state_key: "env.network.latency_high".to_owned(),
        action_key: "route.default_gateway".to_owned(),
        predicted_next_key: "env.network.nominal".to_owned(),
        observed_next_key: "env.network.packet_loss".to_owned(),
        latency_ms: 420,
        token_cost: 900,
    };

    let obs = kernel.observe_transition(&transition);
    assert!(obs.is_ok());
    if let Ok((belief, goal)) = obs {
        assert!(belief.surprise_bps >= 4_000);
        assert!(goal.is_some());
        if let Some(g) = goal {
            assert_eq!(
                g.goal_id,
                "agi.goal.env.network.latency_high.route.default_gateway"
            );
        }
    }

    let policies = vec![
        PolicyCandidate {
            policy_id: "pol.brute_llm".to_owned(),
            action_key: "llm.full_replan".to_owned(),
            pragmatic_value_bps: 7_000,
            epistemic_value_bps: 3_000,
            token_cost: 12_000,
            latency_ms: 3_500,
        },
        PolicyCandidate {
            policy_id: "pol.active_probe_shortcut".to_owned(),
            action_key: "probe.mtu_and_compile_reflex".to_owned(),
            pragmatic_value_bps: 8_500,
            epistemic_value_bps: 9_000,
            token_cost: 400,
            latency_ms: 45,
        },
    ];
    let ranked = select_minimal_free_energy_policy(&policies);
    assert!(ranked.is_ok());
    if let Ok(list) = ranked {
        assert_eq!(
            list.first().map(|p| p.policy_id.as_str()),
            Some("pol.active_probe_shortcut")
        );
    }

    let v1 = AlgorithmicStrategy {
        domain_key: "routing.optimizer".to_owned(),
        strategy_id: "strat.llm_slow".to_owned(),
        generation: 1,
        success_rate_bps: 9_200,
        mean_latency_ms: 850,
        mean_token_cost: 1_500,
        code_complexity_bytes: 1_200,
        proof_digest: "fnv64:1111222233334444".to_owned(),
    };
    assert!(
        kernel
            .evaluate_godel_upgrade(v1)
            .is_ok_and(|verdict| verdict.upgraded)
    );

    let v2_worse = AlgorithmicStrategy {
        domain_key: "routing.optimizer".to_owned(),
        strategy_id: "strat.regression".to_owned(),
        generation: 2,
        success_rate_bps: 8_500,
        mean_latency_ms: 900,
        mean_token_cost: 1_800,
        code_complexity_bytes: 1_400,
        proof_digest: "fnv64:2222333344445555".to_owned(),
    };
    assert!(
        kernel
            .evaluate_godel_upgrade(v2_worse)
            .is_ok_and(|verdict| !verdict.upgraded)
    );

    let v3_pareto = AlgorithmicStrategy {
        domain_key: "routing.optimizer".to_owned(),
        strategy_id: "strat.zero_token_reflex".to_owned(),
        generation: 2,
        success_rate_bps: 9_800,
        mean_latency_ms: 4,
        mean_token_cost: 0,
        code_complexity_bytes: 480,
        proof_digest: "fnv64:9999aaaabbbbcccc".to_owned(),
    };
    let up = kernel.evaluate_godel_upgrade(v3_pareto);
    assert!(up.is_ok());
    if let Ok(verdict) = up {
        assert!(verdict.upgraded);
        assert_eq!(verdict.active_generation, 2);
        assert_eq!(verdict.token_savings_bps, 10_000);
        assert!(verdict.latency_gain_bps > 9_900);
    }
}
