use std::time::{Duration, Instant};

use serde_json::json;

use crate::{
    ConsentKey, ConsentLedger, McpError, McpResult, PolicyConfig, RateLimiter, Risk, Scope,
    Settings, classify, glob_match, parse_tool,
};

fn spec(value: serde_json::Value) -> McpResult<crate::ToolSpec> {
    parse_tool(value, &Settings::default())
}

fn tool(name: &str, description: &str, annotations: &serde_json::Value) -> serde_json::Value {
    json!({"name": name, "description": description, "inputSchema": {"type":"object"}, "annotations": annotations})
}

#[test]
fn classification_never_trusts_hints_downwards_by_default() -> McpResult<()> {
    let config = PolicyConfig::default();
    let lying = spec(tool(
        "list_things",
        "lists",
        &json!({"readOnlyHint": true, "openWorldHint": false}),
    ))?;
    assert_eq!(classify(&lying, false, &config), Risk::Files);
    assert_eq!(classify(&lying, true, &config), Risk::Home);
    let bare = spec(json!({"name":"x","inputSchema":{"type":"object"}}))?;
    assert_eq!(classify(&bare, true, &config), Risk::Files);
    let open = spec(tool("fetch", "gets", &json!({"readOnlyHint": true})))?;
    assert_eq!(classify(&open, true, &config), Risk::Personal);
    let danger = spec(tool(
        "cleanup",
        "will delete everything",
        &json!({"readOnlyHint": true, "openWorldHint": false}),
    ))?;
    assert_eq!(classify(&danger, true, &config), Risk::Critical);
    Ok(())
}

#[test]
fn rules_come_from_configuration() -> McpResult<()> {
    let config = PolicyConfig::from_json(
        r#"{"risk_rules":[{"words":["frobnicate"],"fields":["name"],"min_risk":"critical"}]}"#,
    )?;
    let hit = spec(tool(
        "frobnicate_now",
        "d",
        &json!({"readOnlyHint": true, "openWorldHint": false}),
    ))?;
    let miss = spec(tool(
        "delete_all",
        "d",
        &json!({"readOnlyHint": true, "openWorldHint": false}),
    ))?;
    assert_eq!(classify(&hit, true, &config), Risk::Critical);
    assert_eq!(classify(&miss, true, &config), Risk::Home);
    Ok(())
}

#[test]
fn policy_configuration_is_validated() {
    for bad in [
        r#"{"max_result_chars":0}"#,
        r#"{"unknown":1}"#,
        r#"{"rate":{"per_tool_per_min":0}}"#,
        r#"{"risk_rules":[{"words":[],"fields":["name"],"min_risk":"info"}]}"#,
        r#"{"base":"nonsense"}"#,
    ] {
        assert_eq!(
            PolicyConfig::from_json(bad).err(),
            Some(McpError::InvalidSettings),
            "{bad}"
        );
    }
    assert!(PolicyConfig::from_json("{}").is_ok());
}

#[test]
fn glob_matching_covers_edge_cases() {
    assert!(glob_match("*", "anything"));
    assert!(glob_match("fs.*", "fs.read"));
    assert!(glob_match("*.read", "fs.read"));
    assert!(glob_match("f*.r*d", "fs.read"));
    assert!(!glob_match("fs.*", "net.read"));
    assert!(!glob_match("", "x"));
    assert!(glob_match("", ""));
    assert!(glob_match("a**b", "axxb"));
    assert!(!glob_match("abc", "abcd"));
}

#[test]
fn scope_requires_server_tool_and_risk() {
    let scope = Scope {
        servers: vec!["fs".into()],
        tools: vec!["fs.read*".into()],
        max_risk: Risk::Personal,
    };
    assert!(scope.permits("fs", "fs.read_file", Risk::Home));
    assert!(!scope.permits("fs", "fs.write_file", Risk::Home));
    assert!(!scope.permits("net", "fs.read_file", Risk::Home));
    assert!(!scope.permits("fs", "fs.read_file", Risk::Files));
    assert!(!Scope::none().permits("fs", "fs.read_file", Risk::Info));
}

#[test]
fn rate_limiter_refills_and_bounds_keys() {
    let limiter = RateLimiter::new(60, 2);
    let start = Instant::now();
    let granted = (0..100).filter(|_| limiter.allow("k", start)).count();
    assert_eq!(granted, 60);
    assert!(!limiter.allow("k", start));
    assert!(limiter.allow("k", start + Duration::from_secs(2)));
    assert!(limiter.allow("k2", start));
    assert!(!limiter.allow("k3", start));
}

#[test]
fn consent_is_single_use_bound_and_expiring() -> McpResult<()> {
    let ledger = ConsentLedger::new(1_000, 8);
    let key = ConsentKey {
        operation: "op".into(),
        tool: "fs.write".into(),
        args_hash: "h1".into(),
    };
    let now = Instant::now();
    let token = ledger.issue(key.clone(), now)?;
    let other = ConsentKey {
        args_hash: "h2".into(),
        ..key.clone()
    };
    assert_eq!(
        ledger.redeem(&token, &other, now),
        Err(McpError::ConsentDenied)
    );
    assert_eq!(
        ledger.redeem(&token, &key, now),
        Err(McpError::ConsentDenied)
    );
    let token = ledger.issue(key.clone(), now)?;
    assert_eq!(ledger.redeem(&token, &key, now), Ok(()));
    assert_eq!(
        ledger.redeem(&token, &key, now),
        Err(McpError::ConsentDenied)
    );
    let late = ledger.issue(key.clone(), now)?;
    assert_eq!(
        ledger.redeem(&late, &key, now + Duration::from_secs(5)),
        Err(McpError::ConsentDenied)
    );
    assert_eq!(
        ledger.redeem("forged", &key, now),
        Err(McpError::ConsentDenied)
    );
    Ok(())
}
