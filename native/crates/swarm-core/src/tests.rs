use nuxiva_agent_core::manifest::validate as validate_manifest;

use crate::catalog::{Catalog, intent_slug};
use crate::error::SwarmError;
use crate::settings::Settings;
use crate::wire::{
    Constraints, Edge, Ident, Level, Percept, Plan, SCHEMA_VERSION, Step, StepBudget, TaskEnvelope,
    Validate, VerifySpec, WorkerError, WorkerErrorKind, decode, encode,
};

fn id(text: &str) -> Ident {
    Ident::new(text).unwrap_or_else(|_| unreachable!("fixture id invalid"))
}

fn step(name: &str, template: &str, intent: &str) -> Step {
    Step {
        id: id(name),
        worker_template: id(template),
        intent: id(intent),
        goal_ref: id("goal.one"),
        needs_graph: false,
        budget: StepBudget {
            tokens: 1_000,
            tool_calls: 4,
            time_ms: 10_000,
        },
        verify: VerifySpec::Judge,
    }
}

fn plan(steps: Vec<Step>, edges: &[(&str, &str)]) -> Plan {
    Plan {
        schema_version: SCHEMA_VERSION,
        id: id("plan.one"),
        steps,
        edges: edges
            .iter()
            .map(|(a, b)| Edge {
                from: id(a),
                to: id(b),
            })
            .collect(),
    }
}

fn percept_json(extra: &str) -> String {
    format!(r#"{{"schema_version":1,"id":"p1","at_ms":5,"channel":"voice","text":"ciao"{extra}}}"#)
}

fn catalog() -> Catalog {
    let manifests: Vec<_> = [
        r#"{"id":"cuoco","name":"Cuoco","capabilities":["Ricette","Cena"],"worker":{"kind":"mcp","tokens_max":4000,"needs_graph":true}}"#,
        r#"{"id":"musica","name":"Musica","capabilities":["Riproduzione musicale"]}"#,
    ]
    .iter()
    .filter_map(|raw| validate_manifest(raw, "x", None).manifest)
    .collect();
    Catalog::build(&manifests, &Settings::default())
        .unwrap_or_else(|_| unreachable!("catalog rejected"))
}

#[test]
fn percept_round_trips_and_rejects_unknown_fields() {
    let settings = Settings::default();
    let raw = percept_json(r#","speaker":"anna","presence":["anna","luca"]"#);
    let value: Percept = decode(raw.as_bytes(), &settings).unwrap_or_else(|_| unreachable!());
    let bytes = encode(&value, &settings).unwrap_or_else(|_| unreachable!());
    let again: Percept = decode(&bytes, &settings).unwrap_or_else(|_| unreachable!());
    assert_eq!(value, again);
    let hostile = percept_json(r#","extra":1"#);
    assert_eq!(
        decode::<Percept>(hostile.as_bytes(), &settings).err(),
        Some(SwarmError::Parse)
    );
}

#[test]
fn percept_limits_and_control_characters_are_enforced() {
    let settings = Settings::default();
    let long = "x".repeat(settings.max_text_chars + 1);
    let raw = percept_json("").replace("ciao", &long);
    assert_eq!(
        decode::<Percept>(
            raw.as_bytes(),
            &Settings {
                max_payload_bytes: 1 << 20,
                ..Settings::default()
            }
        )
        .err(),
        Some(SwarmError::TooLarge)
    );
    let control = percept_json("").replace("ciao", "a\\u0007b");
    assert_eq!(
        decode::<Percept>(control.as_bytes(), &settings).err(),
        Some(SwarmError::Invalid)
    );
    let bad_ident = percept_json(r#","speaker":"Anna Rossi""#);
    assert_eq!(
        decode::<Percept>(bad_ident.as_bytes(), &settings).err(),
        Some(SwarmError::Parse)
    );
    let crowd = (0..=settings.max_presence)
        .map(|n| format!("\"p{n}\""))
        .collect::<Vec<_>>()
        .join(",");
    let many = percept_json(&format!(r#","presence":[{crowd}]"#));
    assert_eq!(
        decode::<Percept>(many.as_bytes(), &settings).err(),
        Some(SwarmError::TooLarge)
    );
    let version = percept_json("").replace(r#""schema_version":1"#, r#""schema_version":2"#);
    assert_eq!(
        decode::<Percept>(version.as_bytes(), &settings).err(),
        Some(SwarmError::Version)
    );
}

#[test]
fn oversize_payload_is_rejected_before_parsing() {
    let settings = Settings::default();
    let raw = vec![b' '; settings.max_payload_bytes + 1];
    assert_eq!(
        decode::<Percept>(&raw, &settings).err(),
        Some(SwarmError::TooLarge)
    );
}

#[test]
fn plan_rejects_cycles_duplicates_and_dangling_edges() {
    let settings = Settings::default();
    let steps = || {
        vec![
            step("a", "cuoco", "ricette"),
            step("b", "cuoco", "ricette"),
            step("c", "cuoco", "ricette"),
        ]
    };
    assert!(
        plan(steps(), &[("a", "b"), ("b", "c")])
            .validate(&settings)
            .is_ok()
    );
    assert_eq!(
        plan(steps(), &[("a", "b"), ("b", "c"), ("c", "a")])
            .validate(&settings)
            .err(),
        Some(SwarmError::Cycle)
    );
    assert_eq!(
        plan(steps(), &[("a", "a")]).validate(&settings).err(),
        Some(SwarmError::Cycle)
    );
    assert_eq!(
        plan(steps(), &[("a", "z")]).validate(&settings).err(),
        Some(SwarmError::Invalid)
    );
    let dup = vec![step("a", "cuoco", "ricette"), step("a", "cuoco", "ricette")];
    assert_eq!(
        plan(dup, &[]).validate(&settings).err(),
        Some(SwarmError::Invalid)
    );
    assert_eq!(
        plan(Vec::new(), &[]).validate(&settings).err(),
        Some(SwarmError::TooLarge)
    );
}

#[test]
fn plan_digest_is_stable_and_sensitive() {
    let a = plan(vec![step("a", "cuoco", "ricette")], &[]);
    let mut b = a.clone();
    assert_eq!(a.digest().ok(), b.digest().ok());
    if let Some(first) = b.steps.first_mut() {
        first.budget.tokens = 999;
    }
    assert_ne!(a.digest().ok(), b.digest().ok());
    assert_eq!(a.digest().map(|d| d.as_str().len()).ok(), Some(64));
}

#[test]
fn catalog_comes_only_from_manifests_and_applies_defaults() {
    let catalog = catalog();
    assert_eq!(catalog.len(), 2);
    let cook = catalog
        .template(&id("cuoco"))
        .unwrap_or_else(|| unreachable!());
    assert_eq!(cook.kind, "mcp");
    assert_eq!(cook.tokens_max, 4_000);
    assert_eq!(cook.tool_calls_max, Settings::default().default_tool_calls);
    assert!(cook.needs_graph);
    let music = catalog
        .template(&id("musica"))
        .unwrap_or_else(|| unreachable!());
    assert_eq!(music.kind, "bridge");
    assert_eq!(catalog.agents_for(&id("ricette")), [id("cuoco")]);
    assert_eq!(
        intent_slug("Riproduzione musicale"),
        Some(id("riproduzione_musicale"))
    );
    assert!(catalog.knows_intent(&id("riproduzione_musicale")));
}

#[test]
fn catalog_checks_plans_against_templates_intents_and_budgets() {
    let settings = Settings::default();
    let catalog = catalog();
    let mut good = step("a", "cuoco", "ricette");
    good.needs_graph = true;
    assert!(
        catalog
            .check_plan(&plan(vec![good.clone()], &[]), &settings)
            .is_ok()
    );
    let cases = [
        (
            step("a", "fantasma", "ricette"),
            SwarmError::UnknownTemplate,
        ),
        (step("a", "cuoco", "inventato"), SwarmError::UnknownIntent),
        (
            step("a", "cuoco", "riproduzione_musicale"),
            SwarmError::IntentMismatch,
        ),
        (good.clone(), SwarmError::Budget),
    ];
    let mut over = good.clone();
    over.budget.tokens = 4_001;
    let mut no_graph = good;
    no_graph.needs_graph = false;
    for (candidate, expected) in cases {
        let candidate = if expected == SwarmError::Budget {
            over.clone()
        } else {
            candidate
        };
        assert_eq!(
            catalog
                .check_plan(&plan(vec![candidate], &[]), &settings)
                .err(),
            Some(expected)
        );
    }
    assert_eq!(
        catalog
            .check_plan(&plan(vec![no_graph], &[]), &settings)
            .err(),
        Some(SwarmError::Invalid)
    );
}

#[test]
fn catalog_rejects_duplicate_agents_and_budgets_above_ceilings() {
    let settings = Settings::default();
    let first = validate_manifest(r#"{"id":"cuoco","name":"A"}"#, "cuoco", None).manifest;
    let second = validate_manifest(r#"{"id":"cuoco","name":"B"}"#, "cuoco", None).manifest;
    let pair: Vec<_> = first.into_iter().chain(second).collect();
    assert_eq!(
        Catalog::build(&pair, &settings).err(),
        Some(SwarmError::Invalid)
    );
    let greedy = validate_manifest(
        r#"{"id":"avido","name":"A","worker":{"tokens_max":9000000}}"#,
        "avido",
        None,
    )
    .manifest;
    let list: Vec<_> = greedy.into_iter().collect();
    assert_eq!(
        Catalog::build(&list, &settings).err(),
        Some(SwarmError::Budget)
    );
}

#[test]
fn task_envelope_enforces_constraints_depth_and_known_intent() {
    let settings = Settings::default();
    let catalog = catalog();
    let task = TaskEnvelope {
        schema_version: SCHEMA_VERSION,
        id: id("t1"),
        intent: id("ricette"),
        input: id("p1"),
        constraints: Constraints {
            risk_max: 2,
            deadline_ms: 5_000,
            tokens_max: 1_000,
            tool_calls_max: 4,
            level: Level::Standard,
        },
        parent: None,
        context_ref: None,
        graph_ref: None,
        depth: 0,
    };
    assert!(catalog.check_task(&task, &settings).is_ok());
    let mut deep = task.clone();
    deep.depth = 3;
    assert_eq!(deep.validate(&settings).err(), Some(SwarmError::Budget));
    let mut risky = task.clone();
    risky.constraints.risk_max = 5;
    assert_eq!(risky.validate(&settings).err(), Some(SwarmError::Budget));
    let mut unknown = task;
    unknown.intent = id("sconosciuto");
    assert_eq!(
        catalog.check_task(&unknown, &settings).err(),
        Some(SwarmError::UnknownIntent)
    );
}

#[test]
fn settings_reject_values_above_ceilings_and_unknown_keys() {
    assert!(Settings::default().validate().is_ok());
    assert_eq!(
        Settings::from_json(r#"{"max_steps":0}"#).err(),
        Some(SwarmError::Settings)
    );
    assert_eq!(
        Settings::from_json(r#"{"max_steps":100000}"#).err(),
        Some(SwarmError::Settings)
    );
    assert_eq!(
        Settings::from_json(r#"{"inventato":1}"#).err(),
        Some(SwarmError::Settings)
    );
    assert_eq!(
        Settings::from_json(r#"{"default_worker_kind":"Bad Kind"}"#).err(),
        Some(SwarmError::Settings)
    );
    assert_eq!(
        Settings::from_json(r#"{"default_tokens":300000}"#).err(),
        Some(SwarmError::Settings)
    );
    assert!(Settings::from_json(r#"{"max_steps":8,"max_edges":16}"#).is_ok());
}

#[test]
fn worker_error_marks_retryable_kinds_and_codes_round_trip() {
    let retry = WorkerError::new(
        WorkerErrorKind::GraphNotConsulted,
        id("swarm.graph"),
        id("a"),
    );
    assert!(retry.retryable);
    let fatal = WorkerError::new(WorkerErrorKind::Denied, id("swarm.denied"), id("a"));
    assert!(!fatal.retryable);
    for error in [
        SwarmError::Parse,
        SwarmError::Cycle,
        SwarmError::Budget,
        SwarmError::Settings,
    ] {
        assert_eq!(SwarmError::from_code(error.code()), Some(error));
    }
}
