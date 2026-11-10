use serde_json::{Value, json};

use super::{HOST, Sandbox, at, call, create, plan};
use crate::engine::Engine;
use crate::error::AgencyError;

#[test]
fn restart_during_review_resumes_from_checkpoint() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("review-resume")?;
    {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
        plan(&mut engine)?;
        let dispatch = call(&mut engine, json!({"op": "dispatch"}))?;
        let started = at(&dispatch, "/started");
        let worker = at(&started, "/0/worker")
            .as_str()
            .unwrap_or_default()
            .to_string();
        let generation = at(&started, "/0/generation").as_u64().unwrap_or(1);

        call(
            &mut engine,
            json!({
                "op": "task_update",
                "project": "shop",
                "task": "design",
                "action": "submit",
                "checkpoint": "Schema architetturale e-commerce completato",
                "worker": worker,
                "generation": generation,
                "tokens": 120,
                "seconds": 5
            }),
        )?;

        let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
        let design = at(&detail, "/tasks")
            .as_array()
            .and_then(|tasks| tasks.iter().find(|t| at(t, "/id") == "design"))
            .cloned()
            .unwrap_or(Value::Null);
        assert_eq!(at(&design, "/status"), "review");
        assert_eq!(
            at(&design, "/checkpoint/deliverable"),
            "Schema architetturale e-commerce completato"
        );
    }

    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    let design = at(&detail, "/tasks")
        .as_array()
        .and_then(|tasks| tasks.iter().find(|t| at(t, "/id") == "design"))
        .cloned()
        .unwrap_or(Value::Null);
    assert_eq!(at(&design, "/status"), "review");
    assert_eq!(
        at(&design, "/checkpoint/deliverable"),
        "Schema architetturale e-commerce completato"
    );

    call(
        &mut engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": "design",
            "action": "approve",
            "tokens": 50,
            "seconds": 2
        }),
    )?;
    let detail_after = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    let design_after = at(&detail_after, "/tasks")
        .as_array()
        .and_then(|tasks| tasks.iter().find(|t| at(t, "/id") == "design"))
        .cloned()
        .unwrap_or(Value::Null);
    assert_eq!(at(&design_after, "/status"), "done");
    Ok(())
}

#[test]
fn revoked_agent_loses_tools_and_late_updates_are_rejected() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("revocation")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let dispatch = call(&mut engine, json!({"op": "dispatch"}))?;
    let started = at(&dispatch, "/started");
    let worker = at(&started, "/0/worker")
        .as_str()
        .unwrap_or_default()
        .to_string();
    let generation = at(&started, "/0/generation").as_u64().unwrap_or(1);

    let files = call(
        &mut engine,
        json!({
            "op": "code_files",
            "project": "shop",
            "worker": worker,
            "generation": generation
        }),
    );
    assert!(files.is_ok());

    call(
        &mut engine,
        json!({
            "op": "assignment_revoke",
            "project": "shop",
            "task": "design"
        }),
    )?;

    let files_after = call(
        &mut engine,
        json!({
            "op": "code_files",
            "project": "shop",
            "worker": worker,
            "generation": generation
        }),
    );
    assert!(files_after.is_err());

    let search_after = call(
        &mut engine,
        json!({
            "op": "code_search",
            "project": "shop",
            "query": "test",
            "worker": worker,
            "generation": generation
        }),
    );
    assert!(search_after.is_err());

    let late_update = call(
        &mut engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": "design",
            "action": "submit",
            "checkpoint": "Tentativo tardivo",
            "worker": worker,
            "generation": generation
        }),
    );
    assert!(late_update.is_err());
    Ok(())
}

#[test]
fn restart_interrupts_running_tasks() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("restart")?;
    {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
        plan(&mut engine)?;
        call(&mut engine, json!({"op": "dispatch"}))?;
    }
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    let design = at(&detail, "/tasks")
        .as_array()
        .and_then(|tasks| tasks.iter().find(|t| at(t, "/id") == "design"))
        .map(|t| (at(t, "/status"), at(t, "/attempts")));
    assert_eq!(design, Some((json!("pending"), json!(0))));
    Ok(())
}

#[test]
fn rejected_task_update_preserves_project_snapshot() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("rejected-update")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let before = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    let rejected = call(
        &mut engine,
        json!({"op": "task_update", "project": "shop", "task": "design",
               "action": "approve", "tokens": 500, "seconds": 10}),
    );
    assert!(rejected.is_err());
    let after = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    assert_eq!(before, after);
    Ok(())
}
