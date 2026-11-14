use std::fs;

use serde_json::json;

use super::{HOST, Sandbox, at, call, create, plan, task};
use crate::engine::Engine;
use crate::error::AgencyError;
use crate::protocol::Request;

#[test]
fn full_project_lifecycle() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("life")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    assert!(sandbox.root.join("share/negozio").is_dir());
    plan(&mut engine)?;
    let started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&started, "/started").as_array().map(Vec::len), Some(1));
    task(&mut engine, "design", "submit")?;
    task(&mut engine, "design", "approve")?;
    let started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&started, "/started").as_array().map(Vec::len), Some(2));
    for id in ["api", "ui"] {
        task(&mut engine, id, "submit")?;
        task(&mut engine, id, "approve")?;
    }
    let detail = call(&mut engine, json!({"op": "project_get", "id": "shop"}))?;
    assert_eq!(at(&detail, "/project/status"), "completed");
    assert_eq!(at(&detail, "/progress/percent"), 100);
    Ok(())
}

#[test]
fn rejects_traversal_duplicates_and_unknown_fields() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("reject")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let escape = call(
        &mut engine,
        json!({"op": "project_create", "id": "x", "title": "x", "goal": "x",
               "workspace": "../etc", "budget": {"tokens": 1, "seconds": 1, "parallel": 1}}),
    );
    assert!(escape.is_err());
    assert!(!sandbox.root.join("etc").exists());
    create(&mut engine)?;
    assert!(matches!(create(&mut engine), Err(AgencyError::Exists)));
    assert!(serde_json::from_value::<Request>(json!({"op": "ping", "evil": 1})).is_err());
    Ok(())
}

#[test]
fn budget_exhaustion_pauses_the_project() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("budget")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    call(
        &mut engine,
        json!({"op": "project_create", "id": "shop", "title": "N", "goal": "G",
               "workspace": "n", "budget": {"tokens": 5, "seconds": 3600, "parallel": 1}}),
    )?;
    plan(&mut engine)?;
    call(&mut engine, json!({"op": "dispatch"}))?;
    let detail = task(&mut engine, "design", "submit")?;
    assert_eq!(at(&detail, "/project/status"), "paused");
    let started = call(&mut engine, json!({"op": "dispatch"}))?;
    assert_eq!(at(&started, "/started").as_array().map(Vec::len), Some(0));
    Ok(())
}

#[test]
fn cancel_closes_every_open_task() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("cancel")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    call(&mut engine, json!({"op": "dispatch"}))?;
    let detail = call(
        &mut engine,
        json!({"op": "project_control", "id": "shop", "action": "cancel"}),
    )?;
    assert_eq!(at(&detail, "/project/status"), "cancelled");
    for status in at(&detail, "/tasks")
        .as_array()
        .unwrap_or(&Vec::new())
        .iter()
        .map(|t| at(t, "/status"))
    {
        assert_eq!(status, "cancelled");
    }
    Ok(())
}

#[test]
fn settings_drive_capacity() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("settings")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    let manual = call(
        &mut engine,
        json!({"op": "settings_set",
               "scheduler": {"mode": "manual", "manual_parallel": 3, "max_parallel": 8, "reserve_ram_mb": 1024},
               "model": {"kind": "cloud", "requests_per_minute": 60}}),
    )?;
    assert_eq!(at(&manual, "/capacity/parallel_agents"), 3);
    let bad = call(
        &mut engine,
        json!({"op": "settings_set",
               "scheduler": {"mode": "auto", "manual_parallel": 0, "max_parallel": 8, "reserve_ram_mb": 0},
               "model": {"kind": "local", "size_mb": 100}}),
    );
    assert!(bad.is_err());
    drop(engine);
    let mut reopened = Engine::open(sandbox.config(), HOST)?;
    assert_eq!(
        at(
            &call(&mut reopened, json!({"op": "settings_get"}))?,
            "/scheduler/manual_parallel"
        ),
        3
    );
    Ok(())
}

#[test]
fn code_search_stays_inside_the_project() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("search")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    let shop = sandbox.root.join("share/negozio");
    fs::write(
        shop.join("main.rs"),
        "fn main() { println!(\"secret\"); }\n",
    )?;
    fs::create_dir_all(shop.join("src"))?;
    fs::write(
        shop.join("src/lib.rs"),
        "pub fn token() -> &'static str { \"secret\" }\n",
    )?;
    let outside = sandbox.root.join("share/secret.txt");
    fs::write(&outside, "secret-outside\n")?;
    let hits = call(
        &mut engine,
        json!({"op": "code_search", "project": "shop", "query": "secret"}),
    )?;
    let lines = at(&hits, "/hits")
        .as_array()
        .unwrap_or(&Vec::new())
        .iter()
        .map(|h| at(h, "/path").as_str().unwrap_or_default().to_owned())
        .collect::<Vec<_>>();
    assert_eq!(lines.len(), 2);
    assert!(!lines.iter().any(|p| p.contains("secret.txt")));
    assert!(
        call(
            &mut engine,
            json!({"op": "code_search", "project": "ghost", "query": "x"})
        )
        .is_err()
    );
    assert!(call(&mut engine, json!({"op": "code_files", "project": "ghost"})).is_err());
    Ok(())
}

#[test]
fn manages_rename_archive_assign_and_delete() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("manage")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let renamed = call(
        &mut engine,
        json!({"op": "project_rename", "id": "shop", "title": "Negozio nuovo"}),
    )?;
    assert_eq!(at(&renamed, "/project/title"), "Negozio nuovo");
    assert!(
        call(
            &mut engine,
            json!({"op": "project_rename", "id": "shop", "title": "   "})
        )
        .is_err()
    );
    let assigned = call(
        &mut engine,
        json!({"op": "project_assign", "id": "shop", "agents": ["coder", "critic", "coder"]}),
    )?;
    assert_eq!(
        at(&assigned, "/project/assignees"),
        json!(["coder", "critic"])
    );
    assert!(
        call(
            &mut engine,
            json!({"op": "project_assign", "id": "shop", "agents": ["../x"]})
        )
        .is_err()
    );
    assert!(
        call(
            &mut engine,
            json!({"op": "project_archive", "id": "shop", "archived": true})
        )
        .is_err()
    );
    call(
        &mut engine,
        json!({"op": "project_control", "id": "shop", "action": "pause"}),
    )?;
    let archived = call(
        &mut engine,
        json!({"op": "project_archive", "id": "shop", "archived": true}),
    )?;
    assert_eq!(at(&archived, "/project/archived"), true);
    assert!(
        call(
            &mut engine,
            json!({"op": "project_delete", "id": "shop", "confirm": "wrong"})
        )
        .is_err()
    );
    call(
        &mut engine,
        json!({"op": "project_delete", "id": "shop", "confirm": "shop"}),
    )?;
    assert!(matches!(
        call(&mut engine, json!({"op": "project_get", "id": "shop"})),
        Err(AgencyError::NotFound)
    ));
    assert!(sandbox.root.join("share/negozio").is_dir());
    let reopened = Engine::open(sandbox.config(), HOST)?;
    assert!(reopened.projects.is_empty());
    Ok(())
}

#[test]
fn running_project_cannot_be_deleted() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("nodelete")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    assert!(
        call(
            &mut engine,
            json!({"op": "project_delete", "id": "shop", "confirm": "shop"})
        )
        .is_err()
    );
    Ok(())
}
