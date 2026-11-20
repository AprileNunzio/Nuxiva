use agency_domain::{TaskId, TaskSpec, TaskStatus};

use crate::{PlanError, TaskGraph};

fn spec(id: &str, deps: &[&str], seconds: u64) -> TaskSpec {
    TaskSpec {
        id: id.to_owned(),
        title: format!("Compito {id}"),
        role: "dev".to_owned(),
        depends_on: deps.iter().map(|d| (*d).to_owned()).collect(),
        acceptance: Vec::new(),
        estimate_seconds: seconds,
        max_attempts: 1,
        budget_tokens: None,
        budget_seconds: None,
    }
}

fn id(raw: &str) -> Result<TaskId, PlanError> {
    TaskId::new(raw).map_err(PlanError::from)
}

fn shop() -> Result<TaskGraph, PlanError> {
    TaskGraph::from_specs(&[
        spec("design", &[], 30),
        spec("db", &["design"], 60),
        spec("api", &["db"], 120),
        spec("ui", &["design"], 40),
        spec("e2e", &["api", "ui"], 20),
    ])
}

fn complete(graph: &mut TaskGraph, raw: &str) -> Result<(), PlanError> {
    graph.update(&id(raw)?, |t| {
        t.start()?;
        t.submit()?;
        t.approve()
    })
}

#[test]
fn rejects_unknown_dependency_and_cycles() {
    assert!(matches!(
        TaskGraph::from_specs(&[spec("a", &["ghost"], 1)]),
        Err(PlanError::UnknownDependency { .. })
    ));
    assert_eq!(
        TaskGraph::from_specs(&[spec("a", &["b"], 1), spec("b", &["a"], 1)]).err(),
        Some(PlanError::Cycle)
    );
    assert!(matches!(
        TaskGraph::from_specs(&[spec("a", &[], 1), spec("a", &[], 1)]),
        Err(PlanError::Duplicate(_))
    ));
}

#[test]
fn failed_extend_leaves_graph_untouched() -> Result<(), PlanError> {
    let mut graph = shop()?;
    assert!(
        graph
            .extend(&[spec("x", &[], 1), spec("y", &["nope"], 1)])
            .is_err()
    );
    assert_eq!(graph.len(), 5);
    Ok(())
}

#[test]
fn order_respects_dependencies() -> Result<(), PlanError> {
    let graph = shop()?;
    let order: Vec<&str> = graph.order().iter().map(|i| i.as_str()).collect();
    let pos = |name: &str| order.iter().position(|o| *o == name);
    assert!(pos("design") < pos("db"));
    assert!(pos("db") < pos("api"));
    assert!(pos("api") < pos("e2e"));
    assert!(pos("ui") < pos("e2e"));
    Ok(())
}

#[test]
fn ready_prefers_the_critical_path() -> Result<(), PlanError> {
    let mut graph = shop()?;
    assert_eq!(graph.critical_path_seconds(), 230);
    complete(&mut graph, "design")?;
    let ready: Vec<&str> = graph.ready().iter().map(|i| i.as_str()).collect();
    assert_eq!(ready, ["db", "ui"]);
    assert_eq!(graph.dispatchable(1).len(), 1);
    assert_eq!(graph.critical_path_seconds(), 200);
    Ok(())
}

#[test]
fn failures_block_dependents_transitively() -> Result<(), PlanError> {
    let mut graph = shop()?;
    complete(&mut graph, "design")?;
    graph.update(&id("db")?, |t| {
        t.start()?;
        t.fail()
    })?;
    let blocked: Vec<&str> = graph.blocked().iter().map(|i| i.as_str()).collect();
    assert_eq!(blocked, ["api", "e2e"]);
    complete(&mut graph, "ui")?;
    assert!(graph.is_finished());
    let progress = graph.progress();
    assert_eq!(
        (progress.done, progress.failed, progress.blocked),
        (2, 1, 2)
    );
    assert_eq!(progress.percent, 40);
    Ok(())
}

#[test]
fn remove_only_pending_leaves() -> Result<(), PlanError> {
    let mut graph = shop()?;
    assert!(graph.remove(&id("design")?).is_err());
    assert_eq!(graph.remove(&id("e2e")?)?.status(), TaskStatus::Pending);
    assert_eq!(graph.len(), 4);
    Ok(())
}

#[test]
fn finished_plan_reports_full_progress() -> Result<(), PlanError> {
    let mut graph = shop()?;
    for name in ["design", "db", "ui", "api", "e2e"] {
        complete(&mut graph, name)?;
    }
    assert!(graph.is_finished());
    assert_eq!(graph.progress().percent, 100);
    assert_eq!(graph.ready(), [] as [&agency_domain::TaskId; 0]);
    Ok(())
}

#[test]
fn independent_tasks_dispatch_in_parallel() -> Result<(), PlanError> {
    let mut graph = shop()?;
    complete(&mut graph, "design")?;
    let parallel = graph.dispatchable(2);
    assert_eq!(parallel.len(), 2);
    assert_eq!(
        parallel.first().copied().map(agency_domain::TaskId::as_str),
        Some("db")
    );
    assert_eq!(
        parallel.get(1).copied().map(agency_domain::TaskId::as_str),
        Some("ui")
    );
    Ok(())
}

#[test]
fn test_replan_subgraph_autonomous_recovery() -> Result<(), PlanError> {
    use agency_domain::TaskSpec;

    let specs = vec![
        TaskSpec {
            id: "t_root".into(),
            title: "Root Task".into(),
            role: "dev".into(),
            depends_on: vec![],
            acceptance: vec![],
            estimate_seconds: 10,
            max_attempts: 1,
            budget_tokens: None,
            budget_seconds: None,
        },
        TaskSpec {
            id: "t_middle".into(),
            title: "Middle Task".into(),
            role: "dev".into(),
            depends_on: vec!["t_root".into()],
            acceptance: vec![],
            estimate_seconds: 10,
            max_attempts: 1,
            budget_tokens: None,
            budget_seconds: None,
        },
        TaskSpec {
            id: "t_leaf".into(),
            title: "Leaf Task".into(),
            role: "dev".into(),
            depends_on: vec!["t_middle".into()],
            acceptance: vec![],
            estimate_seconds: 10,
            max_attempts: 1,
            budget_tokens: None,
            budget_seconds: None,
        },
    ];

    let mut graph = TaskGraph::from_specs(&specs)?;
    let middle_id = agency_domain::TaskId::new("t_middle")?;
    let leaf_id = agency_domain::TaskId::new("t_leaf")?;

    complete(&mut graph, "t_root")?;

    graph.update(&middle_id, |t| {
        t.start()?;
        t.fail()
    })?;

    assert!(graph.blocked().contains(&leaf_id));

    let recovery_specs = vec![
        TaskSpec {
            id: "t_middle_fix1".into(),
            title: "Fix Step 1".into(),
            role: "dev".into(),
            depends_on: vec![],
            acceptance: vec![],
            estimate_seconds: 5,
            max_attempts: 1,
            budget_tokens: None,
            budget_seconds: None,
        },
        TaskSpec {
            id: "t_middle_fix2".into(),
            title: "Fix Step 2".into(),
            role: "dev".into(),
            depends_on: vec!["t_middle_fix1".into()],
            acceptance: vec![],
            estimate_seconds: 5,
            max_attempts: 1,
            budget_tokens: None,
            budget_seconds: None,
        },
    ];

    graph.replan_subgraph(&middle_id, &recovery_specs)?;

    let fix1_id = agency_domain::TaskId::new("t_middle_fix1")?;

    assert!(graph.ready().contains(&&fix1_id));

    complete(&mut graph, "t_middle_fix1")?;
    complete(&mut graph, "t_middle_fix2")?;

    assert!(graph.ready().contains(&&leaf_id));
    Ok(())
}

#[test]
fn test_anti_oscillation_guard_lifecycle() {
    use crate::oscillation::{AntiOscillationGuard, OscillationVerdict};

    let mut guard = AntiOscillationGuard::new(3);
    assert_eq!(
        guard.record_failure("git_merge"),
        OscillationVerdict::Permitted { attempt: 1 }
    );
    assert_eq!(
        guard.record_failure("git_merge"),
        OscillationVerdict::Permitted { attempt: 2 }
    );
    assert_eq!(
        guard.record_failure("git_merge"),
        OscillationVerdict::OscillationDetected {
            failures: 3,
            max_allowed: 3
        }
    );

    guard.reset("git_merge");
    assert_eq!(guard.failure_count("git_merge"), 0);
}
