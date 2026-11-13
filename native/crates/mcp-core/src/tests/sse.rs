use crate::{McpError, McpResult, SseParser};

#[test]
fn events_are_split_across_chunks() -> McpResult<()> {
    let mut parser = SseParser::new(1024);
    assert!(parser.feed(b"event: message\r\ndata: {\"a\"")?.is_empty());
    let events = parser.feed(b":1}\r\n\r\n: comment\n\ndata: x\ndata: y\n\n")?;
    assert_eq!(events, vec![b"{\"a\":1}".to_vec(), b"x\ny".to_vec()]);
    Ok(())
}

#[test]
fn oversized_events_are_refused() {
    let mut parser = SseParser::new(8);
    assert_eq!(
        parser.feed(b"data: 0123456789\n").err(),
        Some(McpError::TooLarge)
    );
    let mut parser = SseParser::new(8);
    assert_eq!(parser.feed(b"0123456789").err(), Some(McpError::TooLarge));
}
