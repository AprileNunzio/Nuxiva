use std::time::Duration;

use serde_json::json;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

use crate::{ClientError, LlmClient};

type Check = Result<(), ClientError>;

async fn serve(
    response: Vec<u8>,
) -> Result<(String, tokio::task::JoinHandle<String>), ClientError> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .map_err(|_| ClientError::Transport)?;
    let address = listener.local_addr().map_err(|_| ClientError::Transport)?;
    let task = tokio::spawn(async move {
        let mut seen = String::new();
        if let Ok((mut socket, _)) = listener.accept().await {
            let mut buffer = vec![0_u8; 8192];
            if let Ok(read) = socket.read(&mut buffer).await {
                seen = String::from_utf8_lossy(buffer.get(..read).unwrap_or_default()).into_owned();
            }
            let _ = socket.write_all(&response).await;
            let _ = socket.shutdown().await;
        }
        seen
    });
    Ok((format!("http://{address}"), task))
}

fn http(status: &str, body: &str) -> Vec<u8> {
    format!("HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len())
        .into_bytes()
}

fn client(base: &str) -> Result<LlmClient, ClientError> {
    LlmClient::new(base, Duration::from_secs(5), Duration::from_secs(2))
}

#[tokio::test]
async fn posts_json_and_reads_the_reply() -> Check {
    let (base, task) = serve(http("200 OK", r#"{"response":"ciao"}"#)).await?;
    let reply = client(&base)?
        .post_json("api/generate", &json!({"model": "m"}), None)
        .await?;
    assert_eq!(reply.status, 200);
    assert_eq!(reply.body, r#"{"response":"ciao"}"#);
    let seen = task.await.map_err(|_| ClientError::Transport)?;
    assert!(seen.starts_with("POST /api/generate HTTP/1.1"));
    assert!(seen.contains(r#"{"model":"m"}"#));
    Ok(())
}

#[tokio::test]
async fn error_statuses_are_returned_not_hidden() -> Check {
    let (base, _task) = serve(http("429 Too Many Requests", r#"{"error":"slow"}"#)).await?;
    let reply = client(&base)?
        .post_json("api/generate", &json!({}), None)
        .await?;
    assert_eq!(reply.status, 429);
    Ok(())
}

#[tokio::test]
async fn bearer_header_is_sent() -> Check {
    let (base, task) = serve(http("200 OK", "{}")).await?;
    client(&base)?
        .post_json("v1/chat", &json!({}), Some("secret"))
        .await?;
    let seen = task
        .await
        .map_err(|_| ClientError::Transport)?
        .to_lowercase();
    assert!(seen.contains("authorization: bearer secret"));
    Ok(())
}

#[tokio::test]
async fn redirects_are_not_followed() -> Check {
    let (base, _task) = serve(b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:1/x\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".to_vec()).await?;
    let reply = client(&base)?
        .post_json("api/generate", &json!({}), None)
        .await?;
    assert_eq!(reply.status, 302);
    Ok(())
}

#[test]
fn urls_and_paths_are_validated() {
    let duration = Duration::from_secs(1);
    assert_eq!(
        LlmClient::new("ftp://x", duration, duration).err(),
        Some(ClientError::Url)
    );
    assert_eq!(
        LlmClient::new("http://u:p@host", duration, duration).err(),
        Some(ClientError::Url)
    );
    assert_eq!(
        LlmClient::new("http://host?x=1", duration, duration).err(),
        Some(ClientError::Url)
    );
    assert_eq!(
        LlmClient::new("nonsense", duration, duration).err(),
        Some(ClientError::Url)
    );
}

#[tokio::test]
async fn hostile_paths_are_rejected() -> Check {
    let handle = client("http://127.0.0.1:9")?;
    for path in ["", "../x", "a/../b", "a b", "a?b=1", "//host/x", "a/./b"] {
        assert_eq!(
            handle.post_json(path, &json!({}), None).await.err(),
            Some(ClientError::Url),
            "{path}"
        );
    }
    Ok(())
}

#[tokio::test]
async fn closed_port_is_a_transport_error() -> Check {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .map_err(|_| ClientError::Transport)?;
    let address = listener.local_addr().map_err(|_| ClientError::Transport)?;
    drop(listener);
    let result = client(&format!("http://{address}"))?
        .post_json("api/generate", &json!({}), None)
        .await;
    assert_eq!(result.err(), Some(ClientError::Transport));
    Ok(())
}
