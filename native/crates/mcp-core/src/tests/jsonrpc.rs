use serde_json::{Map, Value, json};

use crate::{
    Id, Implementation, McpError, McpResult, Message, Outcome, cancelled_notification,
    initialize_request, tools_call_request, tools_list_request,
};

const MAX: usize = 1024 * 1024;

fn parse(value: &Value) -> McpResult<Message> {
    Message::parse(value.to_string().as_bytes(), MAX)
}

#[test]
fn request_round_trips() -> McpResult<()> {
    let message = tools_list_request(Id::Number(7), Some("abc"));
    let bytes = message.to_vec()?;
    assert_eq!(Message::parse(&bytes, MAX)?, message);
    Ok(())
}

#[test]
fn builders_produce_valid_messages() -> McpResult<()> {
    let client = Implementation {
        name: "nuxiva".into(),
        version: "1".into(),
        title: None,
    };
    for message in [
        initialize_request(Id::Text("a".into()), "2025-06-18", &client),
        tools_call_request(Id::Number(1), "t", Map::new()),
        cancelled_notification(&Id::Number(1), "stop"),
    ] {
        assert_eq!(Message::parse(&message.to_vec()?, MAX)?, message);
    }
    Ok(())
}

#[test]
fn response_variants_parse() -> McpResult<()> {
    let ok = parse(&json!({"jsonrpc":"2.0","id":1,"result":{"a":1}}))?;
    assert!(matches!(ok, Message::Response(r) if matches!(r.outcome, Outcome::Result(_))));
    let err =
        parse(&json!({"jsonrpc":"2.0","id":"x","error":{"code":-32601,"message":"no\u{202E}pe"}}))?;
    let Message::Response(response) = err else {
        return Err(McpError::InvalidMessage);
    };
    let Outcome::Error(error) = response.outcome else {
        return Err(McpError::InvalidMessage);
    };
    assert_eq!(error.code, -32601);
    assert_eq!(error.message, "nope");
    Ok(())
}

#[test]
fn malformed_messages_are_rejected() {
    let cases = [
        json!([]),
        json!({"id":1,"method":"ping"}),
        json!({"jsonrpc":"1.0","id":1,"method":"ping"}),
        json!({"jsonrpc":"2.0","id":null,"method":"ping"}),
        json!({"jsonrpc":"2.0","id":1.5,"method":"ping"}),
        json!({"jsonrpc":"2.0","id":"","method":"ping"}),
        json!({"jsonrpc":"2.0","id":1,"method":"bad method"}),
        json!({"jsonrpc":"2.0","id":1,"method":"ping","params":[1]}),
        json!({"jsonrpc":"2.0","id":1}),
        json!({"jsonrpc":"2.0"}),
        json!({"jsonrpc":"2.0","id":1,"result":1,"error":{"code":1,"message":"m"}}),
        json!({"jsonrpc":"2.0","id":1,"error":{"code":"x","message":"m"}}),
        json!({"jsonrpc":"2.0","id":1,"error":{"code":1}}),
    ];
    for case in cases {
        assert_eq!(parse(&case), Err(McpError::InvalidMessage), "{case}");
    }
}

#[test]
fn size_and_syntax_limits_apply() {
    assert_eq!(Message::parse(b"{", MAX), Err(McpError::Parse));
    assert_eq!(Message::parse(&[0xff, 0xfe], MAX), Err(McpError::Parse));
    assert_eq!(
        Message::parse(b"{\"jsonrpc\":\"2.0\"}", 4),
        Err(McpError::TooLarge)
    );
    let nested = format!("{}1{}", "[".repeat(10_000), "]".repeat(10_000));
    assert_eq!(
        Message::parse(nested.as_bytes(), MAX * 20),
        Err(McpError::Parse)
    );
}

#[test]
fn notification_has_no_id() -> McpResult<()> {
    let parsed = parse(&json!({"jsonrpc":"2.0","method":"notifications/tools/list_changed"}))?;
    assert!(matches!(parsed, Message::Notification(_)));
    Ok(())
}
