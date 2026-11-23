use serde_json::{Value, json};

use super::{HOST, Sandbox, at, call, create};
use crate::engine::Engine;
use crate::error::AgencyError;

struct Attempt {
    task: String,
    worker: String,
    generation: u64,
}

impl Attempt {
    fn reference(&self) -> Value {
        json!({
            "project": "shop",
            "task": self.task,
            "worker": self.worker,
            "generation": self.generation
        })
    }
}

fn plan_shop(engine: &mut Engine) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({
            "op": "project_plan",
            "id": "shop",
            "decisions": [
                {"id": "stack", "title": "Stack", "rationale": "Backend Rust e vetrina web", "status": "accepted"}
            ],
            "questions": [
                {"id": "payments", "prompt": "Quale gateway di pagamento?", "options": [
                    {"id": "card", "label": "Carta", "description": "Pagamento con carta"},
                    {"id": "bank", "label": "Bonifico", "description": "Bonifico bancario"}
                ]}
            ],
            "tasks": [
                {"id": "design", "title": "Architettura", "role": "architect", "acceptance": ["Schema approvato"]},
                {"id": "api", "title": "API catalogo", "role": "backend", "depends_on": ["design"], "acceptance": ["API testata"]},
                {"id": "ui", "title": "Vetrina", "role": "frontend", "depends_on": ["design"], "acceptance": ["Vetrina navigabile"]},
                {"id": "checkout", "title": "Checkout", "role": "backend", "depends_on": ["api", "ui"], "acceptance": ["Ordine creato"]}
            ]
        }),
    )
}

fn dispatch(engine: &mut Engine) -> Result<Vec<Attempt>, AgencyError> {
    let result = call(engine, json!({"op": "dispatch"}))?;
    let started = at(&result, "/started");
    Ok(started
        .as_array()
        .map(|items| {
            items
                .iter()
                .map(|item| Attempt {
                    task: at(item, "/task").as_str().unwrap_or_default().to_owned(),
                    worker: at(item, "/worker").as_str().unwrap_or_default().to_owned(),
                    generation: at(item, "/generation").as_u64().unwrap_or_default(),
                })
                .collect()
        })
        .unwrap_or_default())
}

fn submit(engine: &mut Engine, attempt: &Attempt, criterion: &str) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({
            "op": "task_update",
            "project": "shop",
            "task": attempt.task,
            "action": "submit",
            "checkpoint": format!("Consegna {}", attempt.task),
            "worker": attempt.worker,
            "generation": attempt.generation,
            "tokens": 100,
            "seconds": 5,
            "proofs": [{
                "criterion": criterion,
                "command": format!("cargo test {}", attempt.task),
                "expected_output": "test result: ok",
                "actual_output": "test result: ok. 3 passed; 0 failed",
                "verified": true,
                "artifact_hash": "sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
            }]
        }),
    )
}

fn approve(engine: &mut Engine, task: &str) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({"op": "task_update", "project": "shop", "task": task, "action": "approve", "tokens": 10, "seconds": 1}),
    )
}

fn pick<'a>(attempts: &'a [Attempt], task: &str) -> Result<&'a Attempt, AgencyError> {
    attempts
        .iter()
        .find(|a| a.task == task)
        .ok_or_else(|| AgencyError::BadRequest(format!("task {task} not started")))
}

fn task_field(detail: &Value, task: &str, pointer: &str) -> Value {
    at(detail, "/tasks")
        .as_array()
        .and_then(|tasks| tasks.iter().find(|t| at(t, "/id") == task))
        .map_or(Value::Null, |t| at(t, pointer))
}

#[test]
fn reference_shop_reaches_proven_artifacts_across_restarts() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("delivery-full")?;
    {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
        let planned = plan_shop(&mut engine)?;
        assert_eq!(at(&planned, "/project/status"), "waiting_user");
        assert!(dispatch(&mut engine)?.is_empty());

        call(
            &mut engine,
            json!({"op": "project_answer", "id": "shop", "question": "payments", "option": "card", "answer": "Carta"}),
        )?;
        let first = dispatch(&mut engine)?;
        let design = pick(&first, "design")?;
        submit(&mut engine, design, "Schema approvato")?;
        approve(&mut engine, "design")?;

        let parallel = dispatch(&mut engine)?;
        assert_eq!(parallel.len(), 2);
    }

    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let resumed = dispatch(&mut engine)?;
    assert_eq!(resumed.len(), 2);
    let api = pick(&resumed, "api")?;
    let ui = pick(&resumed, "ui")?;
    assert!(api.generation >= 2 && ui.generation >= 2);

    call(
        &mut engine,
        json!({
            "op": "forge_propose",
            "attempt": api.reference(),
            "tool": {
                "name": "price_total",
                "description": "Totale ordine",
                "code": "def run(args):\n    return args['price'] * 2\n",
                "tests": [
                    {"args": {"price": 1}, "expect": 2},
                    {"args": {"price": 4}, "expect": 8}
                ],
                "permissions": {"read_paths": ["catalog"]}
            }
        }),
    )?;
    call(
        &mut engine,
        json!({"op": "forge_activate", "name": "price_total", "outcomes": [
            {"case_index": 0, "exit_code": 0, "duration_ms": 2, "stdout_json": 2},
            {"case_index": 1, "exit_code": 0, "duration_ms": 2, "stdout_json": 8}
        ]}),
    )?;
    let granted = call(
        &mut engine,
        json!({"op": "forge_authorize", "attempt": api.reference(), "tool": "price_total", "kind": "read", "target": "catalog/items.json"}),
    )?;
    assert_eq!(at(&granted, "/allowed"), true);
    assert!(
        call(
            &mut engine,
            json!({"op": "forge_authorize", "attempt": api.reference(), "tool": "price_total", "kind": "write", "target": "catalog/items.json"}),
        )
        .is_err()
    );

    submit(&mut engine, api, "API testata")?;
    approve(&mut engine, "api")?;
    submit(&mut engine, ui, "Vetrina navigabile")?;
    approve(&mut engine, "ui")?;

    let last = dispatch(&mut engine)?;
    submit(&mut engine, pick(&last, "checkout")?, "Ordine creato")?;
    approve(&mut engine, "checkout")?;

    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    assert_eq!(at(&detail, "/project/status"), "completed");
    assert_eq!(at(&detail, "/progress/percent"), 100);
    for task in ["design", "api", "ui", "checkout"] {
        assert_eq!(task_field(&detail, task, "/status"), "done", "{task}");
        assert_eq!(
            task_field(&detail, task, "/proofs/0/verified"),
            true,
            "{task}"
        );
        assert!(
            task_field(&detail, task, "/proofs/0/artifact_hash").is_string(),
            "{task}"
        );
    }
    Ok(())
}

#[test]
fn reference_shop_cancellation_during_work_is_final_and_rejects_late_results()
-> Result<(), AgencyError> {
    let sandbox = Sandbox::new("delivery-cancel")?;
    let late = {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
        plan_shop(&mut engine)?;
        call(
            &mut engine,
            json!({"op": "project_answer", "id": "shop", "question": "payments", "option": "bank", "answer": "Bonifico"}),
        )?;
        let first = dispatch(&mut engine)?;
        submit(&mut engine, pick(&first, "design")?, "Schema approvato")?;
        approve(&mut engine, "design")?;
        let running = dispatch(&mut engine)?;
        assert_eq!(running.len(), 2);

        let cancelled = call(
            &mut engine,
            json!({"op": "project_control", "id": "shop", "action": "cancel"}),
        )?;
        assert_eq!(at(&cancelled, "/project/status"), "cancelled");
        let api = pick(&running, "api")?;
        assert!(submit(&mut engine, api, "API testata").is_err());
        assert_eq!(task_field(&cancelled, "design", "/status"), "done");
        Attempt {
            task: api.task.clone(),
            worker: api.worker.clone(),
            generation: api.generation,
        }
    };

    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    assert_eq!(at(&detail, "/project/status"), "cancelled");
    assert!(dispatch(&mut engine)?.is_empty());
    assert!(submit(&mut engine, &late, "API testata").is_err());
    Ok(())
}
