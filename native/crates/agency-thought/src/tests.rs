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
