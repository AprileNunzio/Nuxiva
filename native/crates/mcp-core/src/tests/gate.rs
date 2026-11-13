use std::time::Instant;

use serde_json::{Map, json};

use crate::{
    CallRequest, Gate, McpError, McpResult, PolicyConfig, Risk, Scope, Settings, ToolEntry,
    parse_tool,
};

fn entry(risk: Risk) -> McpResult<ToolEntry> {
    let spec = parse_tool(
        json!({"name":"w","inputSchema":{"type":"object","properties":{"a":{"type":"string"}},"required":["a"]}}),
        &Settings::default(),
    )?;
    Ok(ToolEntry::build("fs", spec, &Settings::default())?.with_risk(risk))
}

fn request(consent: Option<String>) -> CallRequest {
    let mut arguments = Map::new();
    arguments.insert("a".into(), json!("x"));
    CallRequest {
        principal: "p".into(),
        agent: "ag".into(),
        operation: "op".into(),
        arguments,
        consent,
    }
}

fn open_scope() -> Scope {
    Scope {
        servers: vec!["*".into()],
        tools: vec!["*".into()],
        max_risk: Risk::Critical,
    }
}

#[test]
fn low_risk_call_passes() -> McpResult<()> {
    let gate = Gate::new(PolicyConfig::default());
    gate.check(
        &request(None),
        &entry(Risk::Home)?,
        &open_scope(),
        Risk::Critical,
        Instant::now(),
    )
}

#[test]
fn each_denial_reason_is_reported() -> McpResult<()> {
    let gate = Gate::new(PolicyConfig::default());
    let now = Instant::now();
    let home = entry(Risk::Home)?;
    assert_eq!(
        gate.check(
            &request(None),
            &home.with_state(crate::ToolState::Quarantined),
            &open_scope(),
            Risk::Critical,
            now
        ),
        Err(McpError::NotCallable)
    );
    assert_eq!(
        gate.check(
            &request(None),
            &entry(Risk::Files)?,
            &open_scope(),
            Risk::Home,
            now
        ),
        Err(McpError::NotPermitted)
    );
    assert_eq!(
        gate.check(&request(None), &home, &Scope::none(), Risk::Critical, now),
        Err(McpError::NotPermitted)
    );
    let mut bad = request(None);
    bad.arguments.insert("a".into(), json!(1));
    assert_eq!(
        gate.check(&bad, &home, &open_scope(), Risk::Critical, now),
        Err(McpError::InvalidArguments)
    );
    Ok(())
}

#[test]
fn risky_call_needs_one_matching_consent() -> McpResult<()> {
    let gate = Gate::new(PolicyConfig::default());
    let now = Instant::now();
    let files = entry(Risk::Files)?;
    let scope = open_scope();
    assert_eq!(
        gate.check(&request(None), &files, &scope, Risk::Critical, now),
        Err(McpError::ConsentRequired)
    );
    let token = gate
        .consent
        .issue(Gate::consent_key(&request(None), &files), now)?;
    assert_eq!(
        gate.check(
            &request(Some(token.clone())),
            &files,
            &scope,
            Risk::Critical,
            now
        ),
        Ok(())
    );
    assert_eq!(
        gate.check(&request(Some(token)), &files, &scope, Risk::Critical, now),
        Err(McpError::ConsentDenied)
    );
    Ok(())
}

#[test]
fn tainted_operation_needs_consent_even_for_low_risk() -> McpResult<()> {
    let gate = Gate::new(PolicyConfig::default());
    let now = Instant::now();
    let home = entry(Risk::Home)?;
    gate.taint.mark("op");
    assert_eq!(
        gate.check(&request(None), &home, &open_scope(), Risk::Critical, now),
        Err(McpError::ConsentRequired)
    );
    let info = entry(Risk::Info)?;
    assert_eq!(
        gate.check(&request(None), &info, &open_scope(), Risk::Critical, now),
        Ok(())
    );
    Ok(())
}

#[test]
fn rate_limit_is_enforced_per_tool() -> McpResult<()> {
    let config = PolicyConfig::from_json(r#"{"rate":{"per_tool_per_min":3}}"#)?;
    let gate = Gate::new(config);
    let now = Instant::now();
    let home = entry(Risk::Home)?;
    let outcomes: Vec<_> = (0..5)
        .map(|_| gate.check(&request(None), &home, &open_scope(), Risk::Critical, now))
        .collect();
    assert_eq!(outcomes.iter().filter(|o| o.is_ok()).count(), 3);
    assert_eq!(outcomes.last().copied(), Some(Err(McpError::RateLimited)));
    Ok(())
}
