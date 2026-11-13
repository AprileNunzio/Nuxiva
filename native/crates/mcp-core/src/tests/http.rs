use std::time::Duration;

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

use crate::{HttpConfig, Implementation, McpError, McpResult, Session, Settings, spawn_http};

fn client() -> Implementation {
    Implementation {
        name: "nuxiva".into(),
        version: "1".into(),
        title: None,
    }
}

fn find(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack.windows(needle.len()).position(|w| w == needle)
}

async fn read_request(stream: &mut tokio::net::TcpStream) -> Option<(String, Vec<u8>)> {
    let mut data = Vec::new();
    let mut buffer = [0u8; 4096];
    loop {
        let n = stream.read(&mut buffer).await.ok()?;
        if n == 0 {
            return None;
        }
        data.extend_from_slice(buffer.get(..n)?);
        let head_end = find(&data, b"\r\n\r\n")?.checked_add(4)?;
        let head = String::from_utf8_lossy(data.get(..head_end)?).to_lowercase();
        let length = head
            .lines()
            .find_map(|l| l.strip_prefix("content-length: "))
            .and_then(|v| v.trim().parse::<usize>().ok())
            .unwrap_or(0);
        if data.len() >= head_end.checked_add(length)? {
            let body = data.get(head_end..head_end.checked_add(length)?)?.to_vec();
            return Some((head, body));
        }
    }
}

fn respond(body: &serde_json::Value, sse: bool, extra: &str) -> Vec<u8> {
    let payload = if sse {
        format!("event: message\ndata: {body}\n\n")
    } else {
        body.to_string()
    };
    let kind = if sse {
        "text/event-stream"
    } else {
        "application/json"
    };
    format!(
        "HTTP/1.1 200 OK\r\ncontent-type: {kind}\r\ncontent-length: {}\r\nconnection: close\r\n{extra}\r\n{payload}",
        payload.len()
    )
    .into_bytes()
}

async fn serve(listener: TcpListener, sse: bool, fail_tools: bool) {
    loop {
        let Ok((mut stream, _)) = listener.accept().await else {
            return;
        };
        tokio::spawn(async move {
            let Some((head, body)) = read_request(&mut stream).await else {
                return;
            };
            let Ok(message) = serde_json::from_slice::<serde_json::Value>(&body) else {
                return;
            };
            let method = message.get("method").and_then(|m| m.as_str()).unwrap_or("");
            let id = message.get("id").cloned();
            let out = match (method, id) {
                (_, None) => b"HTTP/1.1 202 Accepted\r\ncontent-length: 0\r\nconnection: close\r\n\r\n".to_vec(),
                ("tools/list", _) if fail_tools => {
                    b"HTTP/1.1 500 Internal Server Error\r\ncontent-length: 0\r\nconnection: close\r\n\r\n".to_vec()
                }
                (m, Some(id)) => {
                    let result = super::fake::answer(m, message.get("params")).unwrap_or_default();
                    let needs_token = !head.contains("authorization: bearer secret");
                    if needs_token {
                        b"HTTP/1.1 401 Unauthorized\r\ncontent-length: 0\r\nconnection: close\r\n\r\n".to_vec()
                    } else {
                        let extra = if m == "initialize" { "mcp-session-id: abc\r\n" } else { "" };
                        let body = serde_json::json!({"jsonrpc":"2.0","id":id,"result":result});
                        respond(&body, sse, extra)
                    }
                }
            };
            let _ = stream.write_all(&out).await;
        });
    }
}

async fn start(sse: bool, fail_tools: bool) -> McpResult<String> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .map_err(|_| McpError::Io)?;
    let port = listener.local_addr().map_err(|_| McpError::Io)?.port();
    tokio::spawn(serve(listener, sse, fail_tools));
    Ok(format!("http://127.0.0.1:{port}/mcp"))
}

fn config(url: String, token: &str) -> HttpConfig {
    HttpConfig {
        url,
        headers: vec![("authorization".into(), format!("Bearer {token}"))],
        timeout: Duration::from_secs(5),
        protocol_version: Some("2025-06-18".into()),
        pinned: None,
    }
}

#[tokio::test]
async fn json_and_sse_responses_are_decoded() -> McpResult<()> {
    for sse in [false, true] {
        let url = start(sse, false).await?;
        let link = spawn_http(&config(url, "secret"), 1024 * 1024)?;
        let (session, _, _) = Session::connect(link, Settings::default(), &client()).await?;
        let listing = session.list_tools().await?;
        assert_eq!(listing.tools.len(), 3, "sse={sse}");
    }
    Ok(())
}

#[tokio::test]
async fn bad_token_fails_the_request_instead_of_hanging() -> McpResult<()> {
    let url = start(false, false).await?;
    let link = spawn_http(&config(url, "wrong"), 1024 * 1024)?;
    let outcome = Session::connect(link, Settings::default(), &client()).await;
    assert_eq!(outcome.err(), Some(McpError::Remote));
    Ok(())
}

#[tokio::test]
async fn server_error_becomes_a_remote_error() -> McpResult<()> {
    let url = start(false, true).await?;
    let link = spawn_http(&config(url, "secret"), 1024 * 1024)?;
    let (session, _, _) = Session::connect(link, Settings::default(), &client()).await?;
    assert_eq!(session.list_tools().await.err(), Some(McpError::Remote));
    Ok(())
}

#[tokio::test]
async fn unreachable_server_fails_fast() -> McpResult<()> {
    let link = spawn_http(
        &config("http://127.0.0.1:9/mcp".into(), "secret"),
        1024 * 1024,
    )?;
    let outcome = Session::connect(link, Settings::default(), &client()).await;
    assert_eq!(outcome.err(), Some(McpError::Remote));
    Ok(())
}

#[test]
fn invalid_headers_are_refused() {
    let mut bad = config("http://127.0.0.1:1/".into(), "x");
    bad.headers = vec![("bad header".into(), "v".into())];
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build();
    let outcome = runtime.map(|r| r.block_on(async { spawn_http(&bad, 1024).err() }));
    assert!(matches!(outcome, Ok(Some(McpError::InvalidSettings))));
}
