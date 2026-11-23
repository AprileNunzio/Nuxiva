use serde_json::{Value, json};

use super::{HOST, Sandbox, at, call, create, plan};
use crate::engine::Engine;
use crate::error::AgencyError;

const CODE: &str = "def run(args):\n    return args['price'] * 2\n";

fn attempt(engine: &mut Engine) -> Result<Value, AgencyError> {
    let dispatch = call(engine, json!({"op": "dispatch"}))?;
    let started = at(&dispatch, "/started");
    Ok(json!({
        "project": "shop",
        "task": "design",
        "worker": at(&started, "/0/worker"),
        "generation": at(&started, "/0/generation")
    }))
}

fn proposal() -> Value {
    json!({
        "name": "double_price",
        "description": "Raddoppia il prezzo",
        "args_schema": {"price": "prezzo"},
        "code": CODE,
        "tests": [
            {"args": {"price": 1}, "expect": 2},
            {"args": {"price": 5}, "expect": 10}
        ],
        "permissions": {
            "read_paths": ["catalog"],
            "write_paths": ["out/reports"],
            "network_hosts": ["api.example.com"]
        }
    })
}

fn outcomes() -> Value {
    json!([
        {"case_index": 0, "exit_code": 0, "duration_ms": 3, "stdout_json": 2},
        {"case_index": 1, "exit_code": 0, "duration_ms": 4, "stdout_json": 10}
    ])
}

fn authorize(
    engine: &mut Engine,
    attempt: &Value,
    kind: &str,
    target: &str,
) -> Result<Value, AgencyError> {
    call(
        engine,
        json!({"op": "forge_authorize", "attempt": attempt, "tool": "double_price", "kind": kind, "target": target}),
    )
}

#[test]
fn tool_access_is_limited_to_granted_scope_and_lifecycle() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("forge-scope")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let attempt = attempt(&mut engine)?;

    call(
        &mut engine,
        json!({"op": "forge_propose", "attempt": attempt, "tool": proposal()}),
    )?;
    assert!(authorize(&mut engine, &attempt, "read", "catalog/items.json").is_err());

    call(
        &mut engine,
        json!({"op": "forge_activate", "name": "double_price", "outcomes": outcomes()}),
    )?;
    assert_eq!(
        at(
            &authorize(&mut engine, &attempt, "read", "catalog/items.json")?,
            "/allowed"
        ),
        true
    );
    assert!(authorize(&mut engine, &attempt, "write", "out/reports/a.txt").is_ok());
    assert!(authorize(&mut engine, &attempt, "network", "api.example.com").is_ok());

    assert!(authorize(&mut engine, &attempt, "read", "secrets/key").is_err());
    assert!(authorize(&mut engine, &attempt, "read", "../catalog").is_err());
    assert!(authorize(&mut engine, &attempt, "write", "catalog/items.json").is_err());
    assert!(authorize(&mut engine, &attempt, "network", "evil.example.com").is_err());

    call(
        &mut engine,
        json!({"op": "forge_revoke", "name": "double_price", "reason": "ritirato"}),
    )?;
    assert!(authorize(&mut engine, &attempt, "read", "catalog/items.json").is_err());
    Ok(())
}

#[test]
fn stale_attempt_cannot_propose_or_use_tools() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("forge-attempt")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let attempt = attempt(&mut engine)?;
    call(
        &mut engine,
        json!({"op": "forge_propose", "attempt": attempt, "tool": proposal()}),
    )?;
    call(
        &mut engine,
        json!({"op": "forge_activate", "name": "double_price", "outcomes": outcomes()}),
    )?;
    assert!(authorize(&mut engine, &attempt, "read", "catalog/a").is_ok());

    call(
        &mut engine,
        json!({"op": "assignment_revoke", "project": "shop", "task": "design"}),
    )?;
    assert!(authorize(&mut engine, &attempt, "read", "catalog/a").is_err());
    assert!(
        call(
            &mut engine,
            json!({"op": "forge_propose", "attempt": attempt, "tool": proposal()})
        )
        .is_err()
    );

    let forged = json!({
        "project": "shop",
        "task": "design",
        "worker": at(&attempt, "/worker"),
        "generation": 99
    });
    assert!(authorize(&mut engine, &forged, "read", "catalog/a").is_err());
    Ok(())
}

#[test]
fn catalog_and_revocation_survive_restart() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("forge-restart")?;
    let attempt = {
        let mut engine = Engine::open(sandbox.config(), HOST)?;
        create(&mut engine)?;
        plan(&mut engine)?;
        let attempt = attempt(&mut engine)?;
        call(
            &mut engine,
            json!({"op": "forge_propose", "attempt": attempt, "tool": proposal()}),
        )?;
        call(
            &mut engine,
            json!({"op": "forge_activate", "name": "double_price", "outcomes": outcomes()}),
        )?;
        call(
            &mut engine,
            json!({"op": "forge_revoke", "name": "double_price", "reason": "ritirato"}),
        )?;
        attempt
    };
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    assert!(authorize(&mut engine, &attempt, "read", "catalog/a").is_err());
    Ok(())
}

#[test]
fn rejects_unsafe_permissions_and_unproven_activation() -> Result<(), AgencyError> {
    let sandbox = Sandbox::new("forge-invalid")?;
    let mut engine = Engine::open(sandbox.config(), HOST)?;
    create(&mut engine)?;
    plan(&mut engine)?;
    let attempt = attempt(&mut engine)?;

    let unsafe_tool = json!({
        "name": "double_price",
        "description": "x",
        "code": CODE,
        "tests": [
            {"args": {"price": 1}, "expect": 2},
            {"args": {"price": 5}, "expect": 10}
        ],
        "permissions": {"write_paths": ["../outside"]}
    });
    assert!(
        call(
            &mut engine,
            json!({"op": "forge_propose", "attempt": attempt, "tool": unsafe_tool})
        )
        .is_err()
    );

    call(
        &mut engine,
        json!({"op": "forge_propose", "attempt": attempt, "tool": proposal()}),
    )?;
    let wrong = json!([
        {"case_index": 0, "exit_code": 0, "duration_ms": 3, "stdout_json": 3},
        {"case_index": 1, "exit_code": 0, "duration_ms": 4, "stdout_json": 10}
    ]);
    assert!(
        call(
            &mut engine,
            json!({"op": "forge_activate", "name": "double_price", "outcomes": wrong})
        )
        .is_err()
    );
    assert!(authorize(&mut engine, &attempt, "read", "catalog/a").is_err());
    Ok(())
}
