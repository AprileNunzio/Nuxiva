use std::fs;

use serde_json::json;

use crate::engine::Engine;
use crate::error::AgencyError;
use crate::tests::{HOST, Sandbox, at, call, create, plan};

#[test]
fn thought_socratic_and_specialist_endpoints_work() -> Result<(), AgencyError> {
    let sb = Sandbox::new("cognition")?;
    let mut engine = Engine::open(sb.config(), HOST)?;

    let thought = call(
        &mut engine,
        json!({
            "op": "thought_evaluate",
            "candidates": [
                {
                    "id": "rust-modular",
                    "title": "Rust + React Modulare",
                    "summary": "Architettura zero-trust",
                    "stack": ["rust", "postgres", "react", "stripe"],
                    "scalability": 95,
                    "security": 95,
                    "maintainability": 90,
                    "velocity": 85,
                    "cost_efficiency": 90,
                    "risk_penalty": 5
                }
            ]
        }),
    )?;
    assert_eq!(at(&thought, "/selected_id"), json!("rust-modular"));

    let socratic = call(
        &mut engine,
        json!({
            "op": "socratic_interrogate",
            "goal": "Creami un sito e-commerce di informatica",
            "known_decisions": []
        }),
    )?;
    assert_eq!(
        at(&socratic, "/user_escalations/0/id"),
        json!("q-payment-gateway")
    );

    let specialists = call(
        &mut engine,
        json!({
            "op": "specialist_recruit",
            "goal": "Sito e-commerce di informatica",
            "architecture": "Rust + React"
        }),
    )?;
    assert!(
        specialists
            .pointer("/specialists")
            .and_then(|v| v.as_array())
            .is_some_and(|arr| arr.len() >= 5)
    );

    Ok(())
}

#[test]
fn task_expand_and_surgical_code_patch_work() -> Result<(), AgencyError> {
    let sb = Sandbox::new("surgical")?;
    let mut engine = Engine::open(sb.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;

    let expanded = call(
        &mut engine,
        json!({
            "op": "task_expand",
            "project": "shop",
            "task": "api",
            "subtasks": [
                {
                    "suffix": "catalog",
                    "title": "Endpoint catalogo",
                    "role": "backend",
                    "depends_on_suffixes": [],
                    "acceptance": ["200 OK"],
                    "estimate_seconds": 120
                },
                {
                    "suffix": "cart",
                    "title": "Endpoint carrello",
                    "role": "backend",
                    "depends_on_suffixes": ["catalog"],
                    "acceptance": ["200 OK"],
                    "estimate_seconds": 150
                }
            ]
        }),
    )?;
    assert_eq!(
        at(&expanded, "/expansion/added_tasks/0"),
        json!("api_catalog")
    );

    let file_path = sb.root.join("share/negozio/catalog.py");
    fs::write(
        &file_path,
        "def list_items():\n    return []\n\ndef count_items():\n    return 0\n",
    )?;

    let outline = call(
        &mut engine,
        json!({
            "op": "code_outline",
            "project": "shop",
            "path": "catalog.py"
        }),
    )?;
    assert_eq!(at(&outline, "/symbols/0/name"), json!("list_items"));

    let range = call(
        &mut engine,
        json!({
            "op": "code_view_range",
            "project": "shop",
            "path": "catalog.py",
            "start_line": 1,
            "end_line": 2
        }),
    )?;
    assert_eq!(
        at(&range, "/content"),
        json!("1: def list_items():\n2:     return []")
    );

    let patched = call(
        &mut engine,
        json!({
            "op": "code_patch",
            "project": "shop",
            "path": "catalog.py",
            "chunks": [
                {
                    "start_line": 1,
                    "end_line": 2,
                    "target_content": "    return []",
                    "replacement_content": "    return ['gpu', 'cpu']",
                    "allow_multiple": false
                }
            ]
        }),
    )?;
    assert_eq!(at(&patched, "/replacements_applied"), json!(1));
    assert!(fs::read_to_string(&file_path)?.contains("['gpu', 'cpu']"));

    let forge_ok = call(
        &mut engine,
        json!({
            "op": "forge_inspect",
            "name": "calc_iva",
            "code": "def run(args):\n    return args['net'] * 1.22\n"
        }),
    )?;
    assert_eq!(at(&forge_ok, "/ok"), json!(true));

    Ok(())
}
