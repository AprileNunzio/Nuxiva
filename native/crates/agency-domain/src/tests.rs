use std::path::Path;

use crate::{
    Budget, CleanText, DomainError, Project, ProjectId, ProjectStatus, RoleId, Task, TaskId,
    TaskSpec, TaskStatus, Usage, WorkspacePath,
};

fn spec(id: &str, deps: &[&str]) -> TaskSpec {
    TaskSpec {
        id: id.to_owned(),
        title: format!("Compito {id}"),
        role: "backend".to_owned(),
        depends_on: deps.iter().map(|d| (*d).to_owned()).collect(),
        acceptance: vec!["i test passano".to_owned()],
        estimate_seconds: 60,
        max_attempts: 2,
    }
}

#[test]
fn ids_accept_slugs_and_reject_everything_else() {
    assert!(TaskId::new("api-v2_auth").is_ok());
    assert!(RoleId::new("frontend").is_ok());
    for bad in [
        "",
        "-x",
        "Upper",
        "a b",
        "../etc",
        "a/b",
        "é",
        &"a".repeat(65),
    ] {
        assert!(ProjectId::new(bad).is_err(), "{bad} should be rejected");
    }
}

#[test]
fn ids_validate_on_deserialize() {
    assert!(serde_json::from_str::<TaskId>("\"ok-1\"").is_ok());
    assert!(serde_json::from_str::<TaskId>("\"../x\"").is_err());
}

#[test]
fn clean_text_strips_controls_and_bidi() -> Result<(), DomainError> {
    let text = CleanText::new("t", "  ciao\u{0007}\u{202E} mondo\t ", 50)?;
    assert_eq!(text.as_str(), "ciao mondo");
    assert!(CleanText::new("t", " \u{0000} ", 50).is_err());
    assert!(CleanText::new("t", "abcdef", 5).is_err());
    Ok(())
}

#[test]
fn workspace_rejects_traversal_and_absolute_paths() -> Result<(), DomainError> {
    for bad in [
        "", "/etc", "../x", "a/../b", ".git", "a/.ssh", "a\0b", "x/./y", "nome.",
    ] {
        assert!(WorkspacePath::new(bad).is_err(), "{bad} should be rejected");
    }
    let ok = WorkspacePath::new("Progetti/negozio-informatica")?;
    assert_eq!(
        ok.resolve(Path::new("/srv/nuxiva")),
        Path::new("/srv/nuxiva/Progetti/negozio-informatica")
    );
    assert!(WorkspacePath::new(&["a"; 9].join("/")).is_err());
    Ok(())
}

#[test]
fn budget_rejects_zero_and_tracks_usage() -> Result<(), DomainError> {
    assert!(Budget::new(0, 1, 1).is_err());
    assert!(Budget::new(1, 1, 0).is_err());
    let budget = Budget::new(100, 10, 2)?;
    let mut usage = Usage::default();
    usage.record(60, 5)?;
    assert!(budget.allows(&usage));
    usage.record(60, 0)?;
    assert!(!budget.allows(&usage));
    assert_eq!(usage.record(u64::MAX, 0), Err(DomainError::Overflow));
    assert_eq!(usage.tokens(), 120);
    Ok(())
}

#[test]
fn task_rejects_self_dependency_and_bad_role() {
    assert!(Task::from_spec(&spec("a", &["a"])).is_err());
    let mut bad = spec("a", &[]);
    bad.role = "Ruolo Strano".to_owned();
    assert!(Task::from_spec(&bad).is_err());
}

#[test]
fn task_lifecycle_with_rework() -> Result<(), DomainError> {
    let mut task = Task::from_spec(&spec("a", &[]))?;
    assert_eq!(task.status(), TaskStatus::Pending);
    task.start()?;
    task.submit()?;
    task.rework("manca la validazione dell'input")?;
    assert_eq!(task.status(), TaskStatus::Pending);
    assert!(task.feedback().is_some());
    task.start()?;
    task.submit()?;
    assert_eq!(
        task.rework("ancora no"),
        Err(DomainError::AttemptsExhausted)
    );
    assert_eq!(task.status(), TaskStatus::Failed);
    Ok(())
}

#[test]
fn task_approval_verifies_criteria() -> Result<(), DomainError> {
    let mut task = Task::from_spec(&spec("a", &[]))?;
    assert!(task.approve().is_err());
    task.start()?;
    task.submit()?;
    task.approve()?;
    assert!(task.acceptance().iter().all(crate::Criterion::verified));
    assert!(task.status().is_terminal());
    assert!(task.cancel().is_err());
    Ok(())
}

#[test]
fn interrupt_returns_the_attempt() -> Result<(), DomainError> {
    let mut task = Task::from_spec(&spec("a", &[]))?;
    task.start()?;
    task.interrupt()?;
    assert_eq!(task.attempts(), 0);
    assert_eq!(task.status(), TaskStatus::Pending);
    Ok(())
}

#[test]
fn project_status_machine() -> Result<(), DomainError> {
    let mut project = Project::new(
        ProjectId::new("shop")?,
        "Negozio",
        "Crea un e-commerce di informatica",
        WorkspacePath::new("shop")?,
        Budget::new(1_000, 3_600, 4)?,
        1,
    )?;
    assert_eq!(project.status(), ProjectStatus::Planning);
    assert!(project.transition(ProjectStatus::Completed).is_err());
    project.transition(ProjectStatus::Running)?;
    project.transition(ProjectStatus::Paused)?;
    project.transition(ProjectStatus::Running)?;
    project.transition(ProjectStatus::Completed)?;
    assert!(project.transition(ProjectStatus::Running).is_err());
    Ok(())
}
