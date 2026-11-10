use serde_json::json;

use crate::engine::Engine;
use crate::error::AgencyError;
use crate::tests::{HOST, Sandbox, at, call, create};

#[test]
fn ambiguous_request_produces_questions_and_waits_for_user() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("planning-questions")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;

    let detail = call(
        &mut engine,
        json!({
            "op": "project_plan",
            "id": "shop",
            "decisions": [
                {
                    "id": "arch-style",
                    "title": "Architecture Style",
                    "rationale": "Modular monolith for clean domain isolation",
                    "status": "accepted"
                }
            ],
            "questions": [
                {
                    "id": "db-engine",
                    "prompt": "Which database engine should be used?",
                    "options": [
                        {"id": "pg", "label": "PostgreSQL", "description": "Relational"},
                        {"id": "sqlite", "label": "SQLite", "description": "Embedded"}
                    ]
                }
            ],
            "tasks": [
                {"id": "design", "title": "Architettura", "role": "architect", "estimate_seconds": 30},
                {"id": "api", "title": "API catalogo", "role": "backend", "depends_on": ["design"]},
                {"id": "ui", "title": "Vetrina", "role": "frontend", "depends_on": ["design"]}
            ]
        }),
    )?;

    assert_eq!(at(&detail, "/project/status"), json!("waiting_user"));
    assert_eq!(at(&detail, "/project/decisions/0/id"), json!("arch-style"));
    assert_eq!(at(&detail, "/project/questions/0/id"), json!("db-engine"));

    let dispatch_empty = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&dispatch_empty, "/started"), json!([]));

    let answered = call(
        &mut engine,
        json!({
            "op": "project_answer",
            "id": "shop",
            "question": "db-engine",
            "option": "pg",
            "answer": "PostgreSQL selected for production robustness"
        }),
    )?;

    assert_eq!(at(&answered, "/project/status"), json!("running"));
    assert_eq!(
        at(&answered, "/project/questions/0/selected_option"),
        json!("pg")
    );

    let dispatch_started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&dispatch_started, "/started/0/task"), json!("design"));
    Ok(())
}

#[test]
fn independent_tasks_run_in_parallel() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("planning-parallel")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;

    call(
        &mut engine,
        json!({
            "op": "project_plan",
            "id": "shop",
            "tasks": [
                {"id": "design", "title": "Architettura", "role": "architect", "estimate_seconds": 30},
                {"id": "api", "title": "API catalogo", "role": "backend", "depends_on": ["design"]},
                {"id": "ui", "title": "Vetrina", "role": "frontend", "depends_on": ["design"]}
            ]
        }),
    )?;

    let d1 = call(&mut engine, json!({"op": "dispatch"}))?;
    let worker = at(&d1, "/started/0/worker").as_str().unwrap().to_string();
    let generation_nr = at(&d1, "/started/0/generation").as_u64().unwrap();

    call(
        &mut engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": "design",
            "action": "submit",
            "checkpoint": "Architecture deliverable content",
            "worker": worker,
            "generation": generation_nr,
            "tokens": 50,
            "seconds": 5
        }),
    )?;
    call(
        &mut engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": "design",
            "action": "approve",
            "worker": worker,
            "generation": generation_nr,
            "tokens": 10,
            "seconds": 1
        }),
    )?;

    let d2 = call(&mut engine, json!({"op": "dispatch"}))?;
    let started = at(&d2, "/started").as_array().unwrap().clone();
    assert_eq!(started.len(), 2);
    let task_ids: Vec<&str> = started
        .iter()
        .map(|s| s["task"].as_str().unwrap())
        .collect();
    assert!(task_ids.contains(&"api"));
    assert!(task_ids.contains(&"ui"));
    Ok(())
}

#[test]
fn reproducible_completion_proofs_recorded() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("planning-proofs")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;

    call(
        &mut engine,
        json!({
            "op": "project_plan",
            "id": "shop",
            "tasks": [
                {
                    "id": "api",
                    "title": "API catalogo",
                    "role": "backend",
                    "acceptance": ["Endpoint test passes"],
                    "budget_tokens": 10_000,
                    "budget_seconds": 600
                }
            ]
        }),
    )?;

    let d = call(&mut engine, json!({"op": "dispatch"}))?;
    let worker = at(&d, "/started/0/worker").as_str().unwrap().to_string();
    let generation_nr = at(&d, "/started/0/generation").as_u64().unwrap();

    let update = call(
        &mut engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": "api",
            "action": "submit",
            "checkpoint": "API endpoints complete",
            "worker": worker,
            "generation": generation_nr,
            "tokens": 100,
            "seconds": 10,
            "proofs": [
                {
                    "criterion": "Endpoint test passes",
                    "command": "cargo test test_catalog_endpoint",
                    "expected_output": "test result: ok. 1 passed",
                    "actual_output": "test result: ok. 1 passed; 0 failed",
                    "verified": true,
                    "artifact_hash": "sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
                }
            ]
        }),
    )?;

    assert_eq!(at(&update, "/tasks/0/status"), json!("review"));
    assert_eq!(
        at(&update, "/tasks/0/proofs/0/command"),
        json!("cargo test test_catalog_endpoint")
    );
    assert_eq!(at(&update, "/tasks/0/proofs/0/verified"), json!(true));

    let approved = call(
        &mut engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": "api",
            "action": "approve",
            "worker": worker,
            "generation": generation_nr,
            "tokens": 20,
            "seconds": 2
        }),
    )?;

    assert_eq!(at(&approved, "/tasks/0/status"), json!("done"));
    assert_eq!(at(&approved, "/project/status"), json!("completed"));
    Ok(())
}
