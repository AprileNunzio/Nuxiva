use std::fs;
use std::path::{Path, PathBuf};

use crate::{AuditChain, AuditEvent, FileSink, McpError, Risk, Verdict, report_from_file};

fn temp(name: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!("nuxiva-observe-{}-{name}", std::process::id()));
    let _ = fs::remove_file(&path);
    path
}

fn event(tool: &str) -> AuditEvent {
    AuditEvent {
        ts_ms: 1,
        principal: "p".into(),
        agent: "a".into(),
        server: "s".into(),
        tool: tool.into(),
        risk: Risk::Home,
        verdict: Verdict::Completed,
        duration_ms: 2,
        args_hash: "x".into(),
        response_hash: "y".into(),
    }
}

fn written(path: &Path, count: usize) -> Result<(), McpError> {
    let mut chain = AuditChain::new(FileSink::open(path)?);
    for index in 0..count {
        chain.append(event(&format!("t{index}")))?;
    }
    Ok(())
}

#[test]
fn a_missing_file_is_an_empty_intact_chain() -> Result<(), McpError> {
    let report = report_from_file(&temp("missing"), 10)?;
    assert!(report.intact);
    assert_eq!(report.count, 0);
    assert!(report.records.is_empty());
    Ok(())
}

#[test]
fn the_tail_is_bounded_and_the_chain_verified() -> Result<(), McpError> {
    let path = temp("chain");
    written(&path, 12)?;
    let report = report_from_file(&path, 5)?;
    assert!(report.intact);
    assert_eq!(report.count, 12);
    assert_eq!(report.records.len(), 5);
    assert_eq!(report.records.last().map(|r| r.seq), Some(12));
    assert_eq!(report_from_file(&path, 0)?.records.len(), 1);
    let _ = fs::remove_file(&path);
    Ok(())
}

#[test]
fn tampering_is_reported_not_hidden() -> Result<(), McpError> {
    let path = temp("tamper");
    written(&path, 4)?;
    let text = fs::read_to_string(&path).map_err(|_| McpError::Io)?;
    fs::write(&path, text.replacen("\"t1\"", "\"evil\"", 1)).map_err(|_| McpError::Io)?;
    let report = report_from_file(&path, 10)?;
    assert!(!report.intact);
    assert_eq!(report.error, Some(McpError::ChainBroken.code()));
    let _ = fs::remove_file(&path);
    Ok(())
}
