use std::sync::Mutex;
use std::time::Instant;

use nuxiva_agent_core::ceo::{Decision, Level as CeoLevel};
use nuxiva_agent_core::manifest::validate as validate_manifest;

use crate::catalog::Catalog;
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;
use crate::supervisor::{
    Admission, GraphGate, PlanPrompt, Planner, Request, Supervisor, critical_path_ms,
};
use crate::wire::{Digest, Edge, Ident, Plan, Step, StepBudget, TaskEnvelope, VerifySpec};

fn id(text: &str) -> Ident {
    Ident::new(text).expect("id")
}

fn digest(c: char) -> Digest {
    Digest::try_from(c.to_string().repeat(64)).expect("digest")
}

fn catalog() -> Catalog {
    let manifests: Vec<_> = [
        r#"{"id":"cuoco","name":"Cuoco","capabilities":["Ricette","Cena"],"worker":{"kind":"mcp","tokens_max":4000,"needs_graph":true}}"#,
        r#"{"id":"musica","name":"Musica","capabilities":["Riproduzione musicale","Playlist"]}"#,
        r#"{"id":"meteo","name":"Meteo","capabilities":["Previsioni del tempo"]}"#,
    ]
    .iter()
    .filter_map(|raw| validate_manifest(raw, "x", None).manifest)
    .collect();
    Catalog::build(&manifests, &Settings::default()).expect("catalog")
}

fn supervisor() -> Supervisor {
    Supervisor::new(catalog(), Settings::default()).expect("supervisor")
}

fn decision(primary: &str, secondaries: &[&str], level: CeoLevel) -> Decision {
    Decision {
        conversational: false,
        primary: primary.to_owned(),
        secondaries: secondaries.iter().map(|s| (*s).to_owned()).collect(),
        confidence: 0.9,
        heavy: false,
        level,
        needs_reasoning: false,
        ranked: Vec::new(),
    }
}

fn request(text: &str, graph: Option<Digest>) -> Request<'_> {
    Request {
        id: id("t1"),
        input: id("in.1"),
        text,
        context_ref: None,
        graph_ref: graph,
        risk_max: 2,
    }
}

fn task(sup: &Supervisor, d: &Decision, text: &str, graph: Option<Digest>) -> TaskEnvelope {
    match sup.admit(d, &request(text, graph)).expect("admit") {
        Admission::Task(task) => *task,
        Admission::Direct => unreachable!("expected a task"),
    }
}

struct Script {
    answers: Mutex<Vec<SwarmResult<Vec<u8>>>>,
    prompts: Mutex<Vec<PlanPrompt>>,
}

impl Script {
    fn new(answers: Vec<SwarmResult<Vec<u8>>>) -> Self {
        Self {
            answers: Mutex::new(answers),
            prompts: Mutex::new(Vec::new()),
        }
    }

    fn calls(&self) -> usize {
        self.prompts.lock().expect("lock").len()
    }
}

impl Planner for Script {
    fn propose(&self, prompt: &PlanPrompt) -> SwarmResult<Vec<u8>> {
        self.prompts.lock().expect("lock").push(prompt.clone());
        let mut answers = self.answers.lock().expect("lock");
        if answers.is_empty() {
            Err(SwarmError::Parse)
        } else {
            answers.remove(0)
        }
    }
}

fn step(name: &str, template: &str, intent: &str, graph: bool, tokens: u64) -> Step {
    Step {
        id: id(name),
        worker_template: id(template),
        intent: id(intent),
        goal_ref: id("in.1"),
        needs_graph: graph,
        budget: StepBudget {
            tokens,
            tool_calls: 2,
            time_ms: 10_000,
        },
        verify: VerifySpec::Judge,
    }
}

fn plan_json(steps: Vec<Step>, edges: &[(&str, &str)]) -> Vec<u8> {
    let plan = Plan {
        schema_version: 1,
        id: id("p-t1"),
        steps,
        edges: edges
            .iter()
            .map(|(a, b)| Edge {
                from: id(a),
                to: id(b),
            })
            .collect(),
    };
    serde_json::to_vec(&plan).expect("json")
}

fn good_plan() -> Vec<u8> {
    plan_json(
        vec![step("a", "musica", "riproduzione_musicale", false, 1_000)],
        &[],
    )
}

#[test]
fn conversation_and_unknown_requests_go_direct() {
    let sup = supervisor();
    let mut talk = decision("", &[], CeoLevel::Lampo);
    talk.conversational = true;
    assert_eq!(
        sup.admit(&talk, &request("ciao", None)),
        Ok(Admission::Direct)
    );
    let none = decision("", &[], CeoLevel::Lampo);
    assert_eq!(
        sup.admit(&none, &request("boh", None)),
        Ok(Admission::Direct)
    );
}

#[test]
fn admission_picks_the_intent_from_the_request_and_sets_level_limits() {
    let sup = supervisor();
    let t = task(
        &sup,
        &decision("musica", &[], CeoLevel::Lampo),
        "metti una playlist",
        None,
    );
    assert_eq!(t.intent, id("playlist"));
    let limits = Settings::default().levels.lampo;
    assert_eq!(
        (
            t.constraints.tokens_max,
            t.constraints.tool_calls_max,
            t.constraints.deadline_ms
        ),
        (limits.tokens, limits.tool_calls, limits.time_ms)
    );
    let big = task(
        &sup,
        &decision("musica", &[], CeoLevel::Progetto),
        "riproduzione",
        None,
    );
    assert!(big.constraints.tokens_max > t.constraints.tokens_max);
    assert_eq!(big.intent, id("riproduzione_musicale"));
}

#[test]
fn admission_rejects_unknown_agents() {
    let sup = supervisor();
    let d = decision("inesistente", &[], CeoLevel::Lampo);
    assert_eq!(
        sup.admit(&d, &request("x", None)),
        Err(SwarmError::UnknownTemplate)
    );
    let bad = decision("Bad Id", &[], CeoLevel::Lampo);
    assert_eq!(
        sup.admit(&bad, &request("x", None)),
        Err(SwarmError::Invalid)
    );
}

#[test]
fn lightning_plans_never_call_the_planner() {
    let sup = supervisor();
    let d = decision("musica", &[], CeoLevel::Lampo);
    let t = task(&sup, &d, "playlist", None);
    let script = Script::new(Vec::new());
    let plan = sup
        .plan(&t, &d, "playlist", Some(&script), 0)
        .expect("plan");
    assert_eq!(script.calls(), 0);
    assert_eq!(plan.steps.len(), 1);
    assert_eq!(plan.steps.first().map(|s| s.verify), Some(VerifySpec::None));
}

#[test]
fn standard_without_planner_is_deterministic_and_within_budget() {
    let sup = supervisor();
    let d = decision(
        "musica",
        &["meteo", "meteo", "sconosciuto"],
        CeoLevel::Standard,
    );
    let t = task(&sup, &d, "playlist", None);
    let plan = sup.plan(&t, &d, "previsioni", None, 0).expect("plan");
    assert_eq!(plan.steps.len(), 2);
    assert_eq!(
        plan.steps.first().map(|s| s.verify),
        Some(VerifySpec::Judge)
    );
    assert_eq!(plan.steps.get(1).map(|s| s.verify), Some(VerifySpec::None));
    assert_eq!(
        plan.steps.get(1).map(|s| s.intent.clone()),
        Some(id("previsioni_del_tempo"))
    );
    let tokens: u64 = plan.steps.iter().map(|s| s.budget.tokens).sum();
    assert!(tokens <= t.constraints.tokens_max);
    assert_eq!(plan.digest(), plan.digest());
}

#[test]
fn project_level_needs_a_planner() {
    let sup = supervisor();
    let d = decision("musica", &[], CeoLevel::Progetto);
    let t = task(&sup, &d, "playlist", None);
    assert_eq!(
        sup.plan(&t, &d, "playlist", None, 0).err(),
        Some(SwarmError::NoPlanner)
    );
    let script = Script::new(vec![Ok(good_plan())]);
    let plan = sup
        .plan(&t, &d, "playlist", Some(&script), 0)
        .expect("plan");
    assert_eq!(plan.steps.len(), 1);
    assert_eq!(script.calls(), 1);
}

#[test]
fn a_rejected_plan_is_repaired_exactly_once() {
    let sup = supervisor();
    let d = decision("musica", &[], CeoLevel::Progetto);
    let t = task(&sup, &d, "playlist", None);
    let bad = plan_json(
        vec![step("a", "fantasma", "riproduzione_musicale", false, 1_000)],
        &[],
    );
    let script = Script::new(vec![Ok(bad.clone()), Ok(good_plan())]);
    assert!(sup.plan(&t, &d, "x", Some(&script), 0).is_ok());
    assert_eq!(script.calls(), 2);
    let prompts = script.prompts.lock().expect("lock");
    assert_eq!(prompts.first().and_then(|p| p.rejected.clone()), None);
    assert_eq!(
        prompts.get(1).and_then(|p| p.rejected.clone()),
        Some("swarm.plan.unknown_template".to_owned())
    );
    drop(prompts);
    let hopeless = Script::new(vec![Ok(bad.clone()), Ok(bad.clone()), Ok(good_plan())]);
    assert_eq!(
        sup.plan(&t, &d, "x", Some(&hopeless), 0).err(),
        Some(SwarmError::UnknownTemplate)
    );
    assert_eq!(hopeless.calls(), 2);
}

#[test]
fn hostile_plans_are_refused() {
    let sup = supervisor();
    let d = decision("musica", &[], CeoLevel::Progetto);
    let t = task(&sup, &d, "playlist", None);
    let cases: Vec<(Vec<u8>, SwarmError)> = vec![
        (b"not json".to_vec(), SwarmError::Parse),
        (
            plan_json(
                vec![
                    step("a", "musica", "playlist", false, 100),
                    step("b", "musica", "playlist", false, 100),
                ],
                &[("a", "b"), ("b", "a")],
            ),
            SwarmError::Cycle,
        ),
        (
            plan_json(
                vec![step("a", "musica", "playlist", false, 10_000_000)],
                &[],
            ),
            SwarmError::Budget,
        ),
        (
            plan_json(
                vec![step("a", "musica", "previsioni_del_tempo", false, 100)],
                &[],
            ),
            SwarmError::IntentMismatch,
        ),
        (
            plan_json(vec![step("a", "musica", "intento_ignoto", false, 100)], &[]),
            SwarmError::UnknownIntent,
        ),
        (
            plan_json(vec![step("a", "cuoco", "ricette", false, 100)], &[]),
            SwarmError::Invalid,
        ),
        (
            plan_json(
                (0..9)
                    .map(|i| step(&format!("s{i}"), "musica", "playlist", false, 40_000))
                    .collect(),
                &[],
            ),
            SwarmError::Budget,
        ),
    ];
    for (raw, expected) in cases {
        let script = Script::new(vec![Ok(raw.clone()), Ok(raw)]);
        assert_eq!(
            sup.plan(&t, &d, "x", Some(&script), 0).err(),
            Some(expected)
        );
    }
    let broken = Script::new(vec![Err(SwarmError::Serialize), Err(SwarmError::Serialize)]);
    assert_eq!(
        sup.plan(&t, &d, "x", Some(&broken), 0).err(),
        Some(SwarmError::PlannerFailed)
    );
}

#[test]
fn graph_gate_requires_a_fresh_consulted_reference() {
    let sup = supervisor();
    let d = decision("cuoco", &[], CeoLevel::Lampo);
    let none = task(&sup, &d, "ricette", None);
    assert_eq!(
        sup.plan(&none, &d, "ricette", None, 0).err(),
        Some(SwarmError::GraphNotConsulted)
    );
    let reference = digest('a');
    let with = task(&sup, &d, "ricette", Some(reference.clone()));
    assert_eq!(
        sup.plan(&with, &d, "ricette", None, 0).err(),
        Some(SwarmError::GraphNotConsulted)
    );
    sup.gate().issue(reference, 1_000);
    assert!(sup.plan(&with, &d, "ricette", None, 1_001).is_ok());
    let ttl = Settings::default().graph_ref_ttl_ms;
    assert_eq!(
        sup.plan(&with, &d, "ricette", None, 1_000 + ttl + 1).err(),
        Some(SwarmError::GraphStale)
    );
    assert!(sup.plan(&with, &d, "ricette", None, 1_000 + ttl).is_ok());
}

#[test]
fn graph_gate_is_bounded_and_forgets_expired_references() {
    let settings = Settings {
        max_graph_refs: 3,
        ..Settings::default()
    };
    let gate = GraphGate::new(&settings);
    for (i, c) in ['a', 'b', 'c', 'd', 'e'].into_iter().enumerate() {
        gate.issue(digest(c), u64::try_from(i).unwrap_or(0));
    }
    assert_eq!(gate.len(), 3);
    gate.issue(digest('f'), settings.graph_ref_ttl_ms + 100);
    assert_eq!(gate.len(), 1);
    assert!(!gate.is_empty());
}

#[test]
fn critical_path_follows_the_longest_chain() {
    let a = step("a", "musica", "playlist", false, 1);
    let mut b = step("b", "musica", "playlist", false, 1);
    let mut c = step("c", "musica", "playlist", false, 1);
    let d = step("d", "musica", "playlist", false, 1);
    b.budget.time_ms = 30_000;
    c.budget.time_ms = 5_000;
    let plan = Plan {
        schema_version: 1,
        id: id("p"),
        steps: vec![a, b, c, d],
        edges: [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]
            .iter()
            .map(|(x, y)| Edge {
                from: id(x),
                to: id(y),
            })
            .collect(),
    };
    assert_eq!(critical_path_ms(&plan), Some(10_000 + 30_000 + 10_000));
    let cyclic = Plan {
        edges: vec![
            Edge {
                from: id("a"),
                to: id("b"),
            },
            Edge {
                from: id("b"),
                to: id("a"),
            },
        ],
        ..plan
    };
    assert_eq!(critical_path_ms(&cyclic), None);
}

#[test]
fn level_limits_are_validated() {
    let mut settings = Settings::default();
    settings.levels.lampo.tokens = settings.max_tokens + 1;
    assert_eq!(settings.validate(), Err(SwarmError::Settings));
    let settings = Settings {
        repair_attempts: 9,
        ..Settings::default()
    };
    assert_eq!(settings.validate(), Err(SwarmError::Settings));
    assert_eq!(
        Settings::from_json(r#"{"levels":{"lampo":{"tokens":0,"tool_calls":1,"time_ms":1}}}"#),
        Err(SwarmError::Settings)
    );
}

#[test]
fn lightning_planning_is_fast() {
    let sup = supervisor();
    let d = decision("musica", &["meteo"], CeoLevel::Lampo);
    let t = task(&sup, &d, "playlist", None);
    let started = Instant::now();
    for _ in 0..1_000 {
        assert!(sup.plan(&t, &d, "playlist", None, 0).is_ok());
    }
    assert!(started.elapsed().as_millis() < 2_000);
}
