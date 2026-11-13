use std::sync::Arc;
use std::time::{Duration, Instant};

use serde_json::{Map, Value, json};

use super::dynamic::tool_with;
use crate::{
    ChangePolicy, Diff, McpError, McpResult, Registry, Risk, Settings, ToolEntry, ToolSpec,
    ToolState, build_entries, parse_tool,
};

fn spec(name: &str, schema: Value) -> McpResult<ToolSpec> {
    parse_tool(tool_with(name, schema), &Settings::default())
}

fn entry(server: &str, name: &str, schema: Value) -> McpResult<ToolEntry> {
    ToolEntry::build(server, spec(name, schema)?, &Settings::default())
}

fn simple() -> Value {
    json!({"type":"object","properties":{"a":{"type":"string"}},"required":["a"]})
}

#[test]
fn apply_reports_added_removed_and_unchanged() -> McpResult<()> {
    let registry = Registry::new(Settings::default());
    let first = registry.apply(
        "fs",
        vec![entry("fs", "a", simple())?, entry("fs", "b", simple())?],
    )?;
    assert_eq!(first.added.len(), 2);
    let second = registry.apply("fs", vec![entry("fs", "a", simple())?])?;
    assert_eq!(second.removed, ["fs.b"]);
    assert!(second.added.is_empty() && second.modified.is_empty());
    assert!(
        !registry
            .apply("fs", vec![entry("fs", "a", simple())?])?
            .changed()
    );
    assert_eq!(registry.snapshot().len(), 1);
    Ok(())
}

#[test]
fn servers_are_isolated() -> McpResult<()> {
    let registry = Registry::new(Settings::default());
    registry.apply("one", vec![entry("one", "t", simple())?])?;
    registry.apply("two", vec![entry("two", "t", simple())?])?;
    registry.retire("one")?;
    let snapshot = registry.snapshot();
    assert!(snapshot.get("one.t").is_none());
    assert!(snapshot.callable("two.t").is_some());
    let wrong = registry.apply("two", vec![entry("one", "x", simple())?])?;
    assert_eq!(wrong.rejected, 1);
    assert_eq!(
        registry.apply("Bad Id", Vec::new()).err(),
        Some(McpError::InvalidName)
    );
    Ok(())
}

#[test]
fn compatible_change_is_applied_and_incompatible_is_quarantined() -> McpResult<()> {
    let registry = Registry::new(Settings::default());
    registry.apply("fs", vec![entry("fs", "t", simple())?])?;
    let wider = json!({"type":"object","properties":{"a":{"type":"string"},"b":{"type":"integer"}},"required":["a"]});
    let diff = registry.apply("fs", vec![entry("fs", "t", wider)?])?;
    assert_eq!(diff.modified, ["fs.t"]);
    assert!(registry.snapshot().callable("fs.t").is_some());
    let stricter = json!({"type":"object","properties":{"a":{"type":"string"},"b":{"type":"integer"}},"required":["a","b"]});
    let diff = registry.apply("fs", vec![entry("fs", "t", stricter)?])?;
    assert_eq!(diff.quarantined, ["fs.t"]);
    assert!(registry.snapshot().callable("fs.t").is_none());
    assert_eq!(
        registry.snapshot().get("fs.t").map(|e| e.state),
        Some(ToolState::Quarantined)
    );
    Ok(())
}

#[test]
fn description_change_is_quarantined_and_can_be_approved() -> McpResult<()> {
    let registry = Registry::new(Settings::default());
    registry.apply("fs", vec![entry("fs", "t", simple())?])?;
    let mut changed = spec("t", simple())?;
    changed.description = Some("now do something else".into());
    let candidate = ToolEntry::build("fs", changed, &Settings::default())?;
    let diff = registry.apply("fs", vec![candidate])?;
    assert_eq!(diff.quarantined, ["fs.t"]);
    assert_eq!(
        registry.approve("fs.zzz").err(),
        Some(McpError::UnknownTool)
    );
    registry.approve("fs.t")?;
    assert!(registry.snapshot().callable("fs.t").is_some());
    assert_eq!(registry.approve("fs.t").err(), Some(McpError::NotCallable));
    Ok(())
}

#[test]
fn policies_accept_and_quarantine_all_are_honoured() -> McpResult<()> {
    for (policy, expect_quarantine) in [
        (ChangePolicy::Accept, false),
        (ChangePolicy::Quarantine, true),
    ] {
        let settings = Settings {
            change_policy: policy,
            ..Settings::default()
        };
        let registry = Registry::new(settings.clone());
        registry.apply(
            "fs",
            vec![ToolEntry::build("fs", spec("t", simple())?, &settings)?],
        )?;
        let wider = json!({"type":"object","properties":{"a":{"type":"string"},"b":{"type":"integer"}},"required":["a"]});
        let diff = registry.apply(
            "fs",
            vec![ToolEntry::build("fs", spec("t", wider)?, &settings)?],
        )?;
        assert_eq!(!diff.quarantined.is_empty(), expect_quarantine);
    }
    Ok(())
}

#[test]
fn stale_tools_are_not_callable_and_recover_on_rediscovery() -> McpResult<()> {
    let registry = Registry::new(Settings::default());
    registry.apply("fs", vec![entry("fs", "t", simple())?])?;
    assert_eq!(registry.mark_stale("fs")?, 1);
    assert!(registry.snapshot().callable("fs.t").is_none());
    assert!(registry.snapshot().get("fs.t").is_some());
    registry.apply("fs", vec![entry("fs", "t", simple())?])?;
    assert!(registry.snapshot().callable("fs.t").is_some());
    Ok(())
}

#[test]
fn total_cap_is_enforced() -> McpResult<()> {
    let settings = Settings {
        max_tools_total: 3,
        max_tools_per_server: 3,
        ..Settings::default()
    };
    let registry = Registry::new(settings.clone());
    let specs = (0..6)
        .map(|i| spec(&format!("t{i}"), simple()))
        .collect::<McpResult<Vec<_>>>()?;
    let (entries, rejected) = build_entries("fs", specs, &settings, &|_| Risk::Home);
    assert_eq!(rejected, 0);
    let diff = registry.apply("fs", entries)?;
    assert_eq!(diff.added.len(), 3);
    assert_eq!(diff.rejected, 3);
    Ok(())
}

#[test]
fn arguments_are_validated_against_the_compiled_schema() -> McpResult<()> {
    let built = entry("fs", "t", simple())?;
    let mut good = Map::new();
    good.insert("a".into(), json!("x"));
    assert_eq!(built.input.check_arguments(&good), Ok(()));
    let mut bad = Map::new();
    bad.insert("a".into(), json!(5));
    assert_eq!(
        built.input.check_arguments(&bad),
        Err(McpError::InvalidArguments)
    );
    assert_eq!(
        built.input.check_arguments(&Map::new()),
        Err(McpError::InvalidArguments)
    );
    Ok(())
}

#[test]
fn hostile_schemas_are_discarded_fast_without_network() {
    let started = Instant::now();
    let remote =
        json!({"type":"object","properties":{"a":{"$ref":"http://203.0.113.1/schema.json"}}});
    let broken = json!({"type":"object","properties":{"a":{"type":"nonsense"}}});
    let cyclic = json!({"type":"object","$ref":"#"});
    for schema in [remote, broken, cyclic] {
        let outcome =
            spec("t", schema).and_then(|s| ToolEntry::build("fs", s, &Settings::default()));
        let _ = outcome;
    }
    assert!(started.elapsed() < Duration::from_millis(500));
    let remote =
        json!({"type":"object","properties":{"a":{"$ref":"http://203.0.113.1/schema.json"}}});
    let rejected = spec("t", remote).and_then(|s| ToolEntry::build("fs", s, &Settings::default()));
    assert!(rejected.is_err());
}

#[test]
fn five_thousand_tools_load_quickly() -> McpResult<()> {
    let settings = Settings {
        max_tools_per_server: 5_000,
        ..Settings::default()
    };
    let specs = (0..5_000)
        .map(|i| parse_tool(tool_with(&format!("tool_{i}"), simple()), &settings))
        .collect::<McpResult<Vec<_>>>()?;
    let started = Instant::now();
    let (entries, rejected) = build_entries("big", specs, &settings, &|_| Risk::Home);
    let registry = Registry::new(settings);
    let diff = registry.apply("big", entries)?;
    assert_eq!(rejected, 0);
    assert_eq!(diff.added.len(), 5_000);
    assert!(
        started.elapsed() < Duration::from_secs(2),
        "{:?}",
        started.elapsed()
    );
    Ok(())
}

#[test]
fn concurrent_readers_and_writers_never_block() -> McpResult<()> {
    let registry = Arc::new(Registry::new(Settings::default()));
    let mut threads = Vec::new();
    for worker in 0..8 {
        let registry = Arc::clone(&registry);
        threads.push(std::thread::spawn(move || -> McpResult<()> {
            for round in 0..250 {
                if worker == 0 {
                    registry.apply(
                        "fs",
                        vec![entry("fs", &format!("t{}", round % 5), simple())?],
                    )?;
                } else {
                    let snapshot = registry.snapshot();
                    let _ = snapshot.iter().count();
                    let _ = snapshot.callable("fs.t1");
                }
            }
            Ok(())
        }));
    }
    for thread in threads {
        thread.join().map_err(|_| McpError::Closed)??;
    }
    let _: Diff = registry.retire("fs")?;
    Ok(())
}
