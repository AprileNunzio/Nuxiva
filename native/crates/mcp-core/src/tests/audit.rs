use serde_json::json;

use crate::{
    AuditChain, AuditEvent, FileSink, McpError, McpResult, MemorySink, Risk, Verdict, hash_value,
    verify_audit,
};

fn event(tool: &str) -> AuditEvent {
    AuditEvent {
        ts_ms: 1,
        principal: "p".into(),
        agent: "a".into(),
        server: "s".into(),
        tool: tool.into(),
        risk: Risk::Files,
        verdict: Verdict::Completed,
        duration_ms: 5,
        args_hash: hash_value(&json!({"x": 1})),
        response_hash: hash_value(&json!("r")),
    }
}

fn chain_of(n: usize) -> McpResult<Vec<String>> {
    let mut chain = AuditChain::new(MemorySink::default());
    for i in 0..n {
        chain.append(event(&format!("t{i}")))?;
    }
    Ok(chain.sink().lines.clone())
}

#[test]
fn intact_chain_verifies() -> McpResult<()> {
    let lines = chain_of(20)?;
    let (count, _) = verify_audit(lines.iter().map(String::as_str))?;
    assert_eq!(count, 20);
    Ok(())
}

#[test]
fn any_tampering_is_detected() -> McpResult<()> {
    let lines = chain_of(10)?;
    let mut edited = lines.clone();
    if let Some(line) = edited.get_mut(4) {
        *line = line.replace("\"t4\"", "\"evil\"");
    }
    assert_eq!(
        verify_audit(edited.iter().map(String::as_str)).err(),
        Some(McpError::ChainBroken)
    );
    let mut removed = lines.clone();
    removed.remove(3);
    assert_eq!(
        verify_audit(removed.iter().map(String::as_str)).err(),
        Some(McpError::ChainBroken)
    );
    let mut swapped = lines.clone();
    swapped.swap(2, 3);
    assert_eq!(
        verify_audit(swapped.iter().map(String::as_str)).err(),
        Some(McpError::ChainBroken)
    );
    let truncated: Vec<&str> = lines.iter().take(5).map(String::as_str).collect();
    assert!(verify_audit(truncated).is_ok());
    assert_eq!(
        verify_audit(["not json"]).err(),
        Some(McpError::ChainBroken)
    );
    Ok(())
}

#[test]
fn file_sink_persists_and_chain_resumes() -> McpResult<()> {
    let dir = std::env::temp_dir().join(format!("mcp-audit-{}", std::process::id()));
    std::fs::create_dir_all(&dir).map_err(|_| McpError::Io)?;
    let path = dir.join("audit.jsonl");
    let _ = std::fs::remove_file(&path);
    let mut chain = AuditChain::new(FileSink::open(&path)?);
    chain.append(event("a"))?;
    chain.append(event("b"))?;
    let (seq, head) = {
        let (s, h) = chain.head();
        (s, h.to_owned())
    };
    let mut resumed = AuditChain::resume(FileSink::open(&path)?, seq, head);
    resumed.append(event("c"))?;
    let text = std::fs::read_to_string(&path).map_err(|_| McpError::Io)?;
    let (count, _) = verify_audit(text.lines())?;
    assert_eq!(count, 3);
    let _ = std::fs::remove_dir_all(&dir);
    Ok(())
}

#[test]
fn hashes_are_stable_and_content_sensitive() {
    assert_eq!(
        hash_value(&json!({"a":1,"b":2})),
        hash_value(&json!({"b":2,"a":1}))
    );
    assert_ne!(hash_value(&json!({"a":1})), hash_value(&json!({"a":2})));
}
