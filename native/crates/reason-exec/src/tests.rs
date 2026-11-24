use std::collections::{BTreeMap, BTreeSet, VecDeque};

use capability_registry::{Contract, Effect, Origin, Param, Registry, Role, State, ValueType};
use reason_plan::{Plan, Validated, parse, validate};
use reason_understand::{Goal, parse as parse_goal};

use crate::{
    ApprovalGate, Call, Cancel, Executor, Failure, Invoker, Journal, MemoryJournal, Never, Record,
    Status, step_key,
};

fn contract(
    id: &str,
    inputs: &[(&str, ValueType)],
    output: ValueType,
    effects: &[Effect],
    reversible: bool,
) -> Contract {
    Contract {
        id: id.into(),
        version: 1,
        origin: Origin::Local,
        summary: format!("Capability {id}."),
        inputs: inputs
            .iter()
            .map(|(name, ty)| Param {
                name: (*name).into(),
                ty: *ty,
                required: true,
            })
            .collect(),
        output,
        effects: effects.iter().copied().collect::<BTreeSet<_>>(),
        reversible,
        min_role: Role::Family,
        nodes: BTreeSet::from(["server".into()]),
        tags: BTreeSet::new(),
        state: State::Active,
    }
}

fn registry() -> Registry {
    let mut registry = Registry::new();
    for c in [
        contract(
            "image.search",
            &[("subject", ValueType::Text)],
            ValueType::Image,
            &[Effect::Read],
            true,
        ),
        contract(
            "telegram.send_photo",
            &[("photo", ValueType::Image), ("to", ValueType::Contact)],
            ValueType::Text,
            &[Effect::SendExternal],
            false,
        ),
        contract(
            "email.send",
            &[("attachment", ValueType::Image), ("to", ValueType::Contact)],
            ValueType::Text,
            &[Effect::SendExternal],
            false,
        ),
    ] {
        registry.insert(c).expect("insert");
    }
    registry
}

fn goal() -> Goal {
    parse_goal(
        r#"{"intent":"deliver_media","language":"it","effects":["read","send_external"],"entities":[{"role":"subject","ty":"text","value":"San Bernardo","source":"user"},{"role":"recipient","ty":"contact","value":"me@example.org","source":"user"}],"confidence_bps":9500}"#,
        "invia a me@example.org un San Bernardo",
    )
    .expect("goal")
}

const PLAN: &str = r#"{"steps":[
{"id":"find","capability":"image.search","args":{"subject":{"from":"entity","role":"subject"}}},
{"id":"tg","capability":"telegram.send_photo","args":{"photo":{"from":"step","step":"find"},"to":{"from":"entity","role":"recipient"}}},
{"id":"mail","capability":"email.send","args":{"attachment":{"from":"step","step":"find"},"to":{"from":"entity","role":"recipient"}}}]}"#;

fn prepared() -> (Registry, Plan, Validated, Goal) {
    let registry = registry();
    let plan = parse(PLAN).expect("plan");
    let goal = goal();
    let validated = validate(&plan, &registry, Role::Owner, &goal).expect("valid");
    (registry, plan, validated, goal)
}

#[derive(Default)]
struct Script {
    results: BTreeMap<String, VecDeque<Result<String, Failure>>>,
    calls: Vec<(String, BTreeMap<String, String>)>,
}

impl Script {
    fn on(mut self, capability: &str, results: Vec<Result<String, Failure>>) -> Self {
        self.results.insert(capability.into(), results.into());
        self
    }
}

impl Invoker for &mut Script {
    fn invoke(&mut self, call: &Call<'_>) -> Result<String, Failure> {
        self.calls.push((call.capability.into(), call.args.clone()));
        self.results
            .get_mut(call.capability)
            .and_then(VecDeque::pop_front)
            .unwrap_or(Err(Failure::Permanent))
    }
}

struct Gate(BTreeSet<&'static str>, Vec<String>);

impl ApprovalGate for &mut Gate {
    fn approve(&mut self, step: &str, _capability: &str, _args: &BTreeMap<String, String>) -> bool {
        self.1.push(step.into());
        self.0.contains(step)
    }
}

struct Stop;

impl Cancel for Stop {
    fn cancelled(&self) -> bool {
        true
    }
}

fn everything() -> Gate {
    Gate(BTreeSet::from(["tg", "mail"]), Vec::new())
}

#[test]
fn the_photo_is_found_once_and_sent_on_both_channels() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default()
        .on("image.search", vec![Ok("img:1".into())])
        .on("telegram.send_photo", vec![Ok("sent".into())])
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert!(report.complete());
    assert_eq!(gate.1.len(), 2);
    assert_eq!(script.calls.len(), 3);
    let tg = script
        .calls
        .iter()
        .find(|(c, _)| c == "telegram.send_photo")
        .expect("tg");
    assert_eq!(tg.1.get("photo").map(String::as_str), Some("img:1"));
    assert_eq!(tg.1.get("to").map(String::as_str), Some("me@example.org"));
}

#[test]
fn a_denied_approval_sends_nothing_and_never_blocks_other_steps() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default()
        .on("image.search", vec![Ok("img:1".into())])
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = Gate(BTreeSet::from(["mail"]), Vec::new());
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert_eq!(report.get("tg").map(|s| &s.status), Some(&Status::Denied));
    assert!(matches!(
        report.get("mail").map(|s| &s.status),
        Some(Status::Done(_))
    ));
    assert!(script.calls.iter().all(|(c, _)| c != "telegram.send_photo"));
    assert_eq!(report.needs_human(), vec!["tg"]);
}

#[test]
fn a_failed_step_skips_its_dependents_without_calling_them() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default().on("image.search", vec![Err(Failure::Permanent)]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert_eq!(report.get("find").map(|s| &s.status), Some(&Status::Failed));
    assert_eq!(report.get("tg").map(|s| &s.status), Some(&Status::Skipped));
    assert_eq!(
        report.get("mail").map(|s| &s.status),
        Some(&Status::Skipped)
    );
    assert_eq!(script.calls.len(), 1);
    assert!(gate.1.is_empty());
}

#[test]
fn reads_are_retried_but_irreversible_sends_are_never_repeated() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default()
        .on(
            "image.search",
            vec![
                Err(Failure::Retryable),
                Err(Failure::Retryable),
                Ok("img:1".into()),
            ],
        )
        .on(
            "telegram.send_photo",
            vec![Err(Failure::Retryable), Ok("sent".into())],
        )
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert_eq!(report.get("find").map(|s| s.attempts), Some(3));
    assert_eq!(report.get("tg").map(|s| &s.status), Some(&Status::Failed));
    assert_eq!(report.get("tg").map(|s| s.attempts), Some(1));
    assert_eq!(
        script
            .calls
            .iter()
            .filter(|(c, _)| c == "telegram.send_photo")
            .count(),
        1
    );
}

#[test]
fn a_send_that_never_started_can_be_repeated_safely() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default()
        .on("image.search", vec![Ok("img:1".into())])
        .on(
            "telegram.send_photo",
            vec![Err(Failure::NotStarted), Ok("sent".into())],
        )
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert!(report.complete());
    assert_eq!(report.get("tg").map(|s| s.attempts), Some(2));
}

#[test]
fn resuming_replays_finished_steps_without_calling_them_again() {
    let (registry, plan, validated, goal) = prepared();
    let mut first = Script::default()
        .on("image.search", vec![Ok("img:1".into())])
        .on("telegram.send_photo", vec![Ok("sent".into())])
        .on("email.send", vec![Err(Failure::Permanent)]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut first,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    exec.run(&plan, &validated, &goal, "p1").expect("run");
    let journal = exec.journal().clone();
    let mut second = Script::default().on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(&registry, &mut second, &mut gate, journal, Never);
    let report = exec.run(&plan, &validated, &goal, "p1").expect("resume");
    assert!(report.complete());
    assert!(matches!(
        report.get("find").map(|s| &s.status),
        Some(Status::Replayed(_))
    ));
    assert!(matches!(
        report.get("tg").map(|s| &s.status),
        Some(Status::Replayed(_))
    ));
    assert_eq!(second.calls.len(), 1);
}

#[test]
fn a_crash_during_an_irreversible_send_is_never_repeated_blindly() {
    let (registry, plan, validated, goal) = prepared();
    let mut journal = MemoryJournal::new(100);
    let args = BTreeMap::from([
        ("photo".to_owned(), "img:1".to_owned()),
        ("to".to_owned(), "me@example.org".to_owned()),
    ]);
    journal
        .append(&step_key("p1", "tg", &args), Record::Started)
        .expect("append");
    let mut script = Script::default()
        .on("image.search", vec![Ok("img:1".into())])
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(&registry, &mut script, &mut gate, journal, Never);
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert_eq!(
        report.get("tg").map(|s| &s.status),
        Some(&Status::Indeterminate)
    );
    assert!(script.calls.iter().all(|(c, _)| c != "telegram.send_photo"));
    assert!(report.needs_human().contains(&"tg"));
}

#[test]
fn a_different_plan_never_replays_another_plans_results() {
    let (registry, plan, validated, goal) = prepared();
    let mut first = Script::default()
        .on("image.search", vec![Ok("img:1".into())])
        .on("telegram.send_photo", vec![Ok("sent".into())])
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut first,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    exec.run(&plan, &validated, &goal, "p1").expect("run");
    let journal = exec.journal().clone();
    let mut second = Script::default()
        .on("image.search", vec![Ok("img:2".into())])
        .on("telegram.send_photo", vec![Ok("sent".into())])
        .on("email.send", vec![Ok("sent".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(&registry, &mut second, &mut gate, journal, Never);
    exec.run(&plan, &validated, &goal, "p2").expect("run");
    assert_eq!(second.calls.len(), 3);
}

#[test]
fn oversized_output_is_rejected_and_cancellation_stops_everything() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default().on("image.search", vec![Ok("x".repeat(70_000))]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Never,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert_eq!(report.get("find").map(|s| &s.status), Some(&Status::Failed));

    let mut script = Script::default();
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(100),
        Stop,
    );
    let report = exec.run(&plan, &validated, &goal, "p1").expect("run");
    assert!(script.calls.is_empty());
    assert!(
        report
            .steps
            .iter()
            .all(|s| s.status == Status::Cancelled || s.status == Status::Skipped)
    );
}

#[test]
fn a_full_journal_stops_execution_before_acting_unrecorded() {
    let (registry, plan, validated, goal) = prepared();
    let mut script = Script::default().on("image.search", vec![Ok("img:1".into())]);
    let mut gate = everything();
    let mut exec = Executor::new(
        &registry,
        &mut script,
        &mut gate,
        MemoryJournal::new(0),
        Never,
    );
    assert!(exec.run(&plan, &validated, &goal, "p1").is_err());
    assert!(script.calls.is_empty());
}
