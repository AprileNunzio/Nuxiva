use serde_json::{Value, json};

use crate::{
    Content, Feature, McpError, McpResult, Settings, negotiate, parse_call_result,
    parse_initialize_result, parse_tool, parse_tools_page, supported_versions,
};

fn tool(name: &str) -> Value {
    json!({"name": name, "description": "d\u{202E}x", "inputSchema": {"type":"object","properties":{"a":{"type":"string"}}}})
}

#[test]
fn valid_tool_is_sanitized() -> McpResult<()> {
    let spec = parse_tool(tool("read_file"), &Settings::default())?;
    assert_eq!(spec.name, "read_file");
    assert_eq!(spec.description.as_deref(), Some("dx"));
    Ok(())
}

#[test]
fn invalid_tools_are_rejected() {
    let settings = Settings::default();
    let bad_name = tool("bad name");
    let no_schema = json!({"name":"a"});
    let wrong_type = json!({"name":"a","inputSchema":{"type":"string"}});
    let long = tool(&"a".repeat(200));
    for case in [bad_name, no_schema, wrong_type, long] {
        assert_eq!(parse_tool(case, &settings), Err(McpError::InvalidTool));
    }
}

#[test]
fn hostile_schemas_are_bounded() {
    let settings = Settings::default();
    let mut deep = json!({"type":"object"});
    for _ in 0..100 {
        deep = json!({"type":"object","properties":{"x":deep}});
    }
    let bomb = json!({"name":"a","inputSchema":deep});
    assert_eq!(parse_tool(bomb, &settings), Err(McpError::TooDeep));
    let wide: Vec<Value> = (0..30_000).map(|i| json!(i)).collect();
    let flat = json!({"name":"a","inputSchema":{"type":"object","enum":wide}});
    assert!(parse_tool(flat, &settings).is_err());
}

#[test]
fn page_keeps_good_tools_and_reports_bad_ones() -> McpResult<()> {
    let page = json!({"tools":[tool("ok"), json!({"name":"x"})], "nextCursor":"c1"});
    let (tools, cursor) = parse_tools_page(page, &Settings::default())?;
    assert_eq!(tools.len(), 2);
    assert_eq!(tools.iter().filter(|t| t.is_ok()).count(), 1);
    assert_eq!(cursor.as_deref(), Some("c1"));
    Ok(())
}

#[test]
fn oversized_page_is_rejected() {
    let settings = Settings {
        max_tools_per_server: 1,
        ..Settings::default()
    };
    let page = json!({"tools":[tool("a"), tool("b")]});
    assert_eq!(parse_tools_page(page, &settings), Err(McpError::TooLarge));
}

#[test]
fn initialize_and_call_results_parse() -> McpResult<()> {
    let init = parse_initialize_result(json!({
        "protocolVersion":"2025-06-18",
        "capabilities":{"tools":{"listChanged":true}},
        "serverInfo":{"name":"s","version":"1"}
    }))?;
    assert_eq!(init.capabilities.tools.map(|t| t.list_changed), Some(true));
    let result = parse_call_result(json!({
        "content":[{"type":"text","text":"hi"},{"type":"hologram","x":1}],
        "isError":true
    }))?;
    assert!(result.is_error);
    assert_eq!(
        result.content.first(),
        Some(&Content::Text { text: "hi".into() })
    );
    assert_eq!(result.content.get(1), Some(&Content::Unknown));
    Ok(())
}

#[test]
fn versions_are_negotiated_from_the_table() {
    assert_eq!(supported_versions().first(), Some(&"2025-06-18"));
    assert!(negotiate("2024-11-05").is_some_and(|p| !p.has(Feature::StreamableHttp)));
    assert!(negotiate("1999-01-01").is_none());
}
