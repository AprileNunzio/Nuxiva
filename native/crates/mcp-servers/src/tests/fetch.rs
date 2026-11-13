use std::sync::Arc;

use serde_json::{Map, json};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

use nuxiva_mcp_core::{NetworkPolicy, ToolOutput, ToolServer};

use crate::fetch::plain::plain;
use crate::{FetchConfig, FetchServer};

async fn origin(routes: Vec<(&'static str, String)>) -> Result<u16, std::io::Error> {
    let listener = TcpListener::bind("127.0.0.1:0").await?;
    let port = listener.local_addr()?.port();
    let routes = Arc::new(routes);
    tokio::spawn(async move {
        while let Ok((mut stream, _)) = listener.accept().await {
            let routes = Arc::clone(&routes);
            tokio::spawn(async move {
                let mut buffer = vec![0u8; 4096];
                let read = stream.read(&mut buffer).await.unwrap_or(0);
                let head = String::from_utf8_lossy(buffer.get(..read).unwrap_or(&[])).into_owned();
                let path = head.split_whitespace().nth(1).unwrap_or("/").to_owned();
                let reply = routes.iter().find(|(p, _)| *p == path).map_or_else(
                    || {
                        "HTTP/1.1 404 Not Found\r\ncontent-length: 0\r\nconnection: close\r\n\r\n"
                            .to_owned()
                    },
                    |(_, r)| r.clone(),
                );
                let _ = stream.write_all(reply.as_bytes()).await;
                let _ = stream.shutdown().await;
            });
        }
    });
    Ok(port)
}

fn ok(body: &str) -> String {
    format!(
        "HTTP/1.1 200 OK\r\ncontent-type: text/html\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{body}",
        body.len()
    )
}

fn redirect(to: &str) -> String {
    format!(
        "HTTP/1.1 302 Found\r\nlocation: {to}\r\ncontent-length: 0\r\nconnection: close\r\n\r\n"
    )
}

fn local() -> FetchConfig {
    FetchConfig {
        hosts: vec!["127.0.0.1".into()],
        network: NetworkPolicy {
            allow_loopback: true,
            allow_private: false,
            ports: Vec::new(),
        },
        allow_insecure: false,
        ..FetchConfig::default()
    }
}

async fn fetch(config: FetchConfig, url: String) -> Result<ToolOutput, tokio::task::JoinError> {
    let server = FetchServer::new("web", &config).map_err(|_| ()).ok();
    tokio::task::spawn_blocking(move || {
        let mut args = Map::new();
        args.insert("url".into(), json!(url));
        server.map_or_else(|| ToolOutput::fail("config"), |s| s.call("http_get", &args))
    })
    .await
}

#[test]
fn markup_is_reduced_to_text_like_the_legacy_tool() {
    let page = "<html><style>p{}</style><SCRIPT>alert(1)</SCRIPT><p>Ciao</p>  <b>mondo</b>\n<br/>a < b</html>";
    assert_eq!(plain(page, 5000), "Ciao mondo a");
    assert_eq!(plain("<p>abcdefghij</p>", 4), "abcd");
    assert_eq!(plain("<script>x", 100), "");
}

#[test]
fn configuration_is_validated_and_hosts_match_by_suffix() {
    assert!(FetchConfig::default().validate().is_ok());
    let bad = FetchConfig {
        timeout_ms: 0,
        ..FetchConfig::default()
    };
    assert!(bad.validate().is_err());
    let scoped = FetchConfig {
        hosts: vec!["example.com".into(), "*.api.test".into()],
        ..FetchConfig::default()
    };
    assert!(scoped.allows("EXAMPLE.com"));
    assert!(scoped.allows("v1.api.test"));
    assert!(!scoped.allows("api.test"));
    assert!(!scoped.allows("evilexample.com"));
    assert!(!scoped.allows("example.com.evil.test"));
}

#[tokio::test(flavor = "multi_thread")]
async fn a_page_is_fetched_and_reduced() -> Result<(), Box<dyn std::error::Error>> {
    let port = origin(vec![("/", ok("<h1>Titolo</h1><p>corpo</p>"))]).await?;
    let out = fetch(local(), format!("http://127.0.0.1:{port}/")).await?;
    assert!(!out.is_error, "{}", out.text);
    assert_eq!(out.text, "HTTP 200\nTitolo corpo");
    let missing = fetch(local(), format!("http://127.0.0.1:{port}/no")).await?;
    assert_eq!(missing.text, "HTTP 404\n");
    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn the_default_policy_refuses_local_and_unsafe_targets()
-> Result<(), Box<dyn std::error::Error>> {
    let port = origin(vec![("/", ok("x"))]).await?;
    for url in [
        format!("http://127.0.0.1:{port}/"),
        "http://169.254.169.254/latest".into(),
        "http://10.0.0.1/".into(),
        "http://93.184.216.34/".into(),
        "ftp://example.com/".into(),
        "file:///etc/passwd".into(),
        "https://user:pw@example.com/".into(),
        "not a url".into(),
    ] {
        let out = fetch(FetchConfig::default(), url.clone()).await?;
        assert!(out.is_error, "{url}");
    }
    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn hosts_outside_the_allowlist_and_wrong_ports_are_refused()
-> Result<(), Box<dyn std::error::Error>> {
    let port = origin(vec![("/", ok("x"))]).await?;
    let other = FetchConfig {
        hosts: vec!["example.org".into()],
        ..local()
    };
    assert!(
        fetch(other, format!("http://127.0.0.1:{port}/"))
            .await?
            .is_error
    );
    let ported = FetchConfig {
        network: NetworkPolicy {
            allow_loopback: true,
            allow_private: false,
            ports: vec![443],
        },
        ..local()
    };
    assert!(
        fetch(ported, format!("http://127.0.0.1:{port}/"))
            .await?
            .is_error
    );
    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn redirects_are_followed_revalidated_and_bounded() -> Result<(), Box<dyn std::error::Error>>
{
    let port = origin(vec![
        ("/a", redirect("/b")),
        ("/b", ok("arrivato")),
        ("/meta", redirect("http://169.254.169.254/latest")),
        ("/loop", redirect("/loop")),
    ])
    .await?;
    let base = format!("http://127.0.0.1:{port}");
    let followed = fetch(local(), format!("{base}/a")).await?;
    assert_eq!(followed.text, "HTTP 200\narrivato");
    assert!(fetch(local(), format!("{base}/meta")).await?.is_error);
    let looped = fetch(local(), format!("{base}/loop")).await?;
    assert!(looped.is_error);
    assert!(looped.text.contains("reindirizzamenti"));
    Ok(())
}

#[tokio::test(flavor = "multi_thread")]
async fn bodies_are_capped_before_they_are_decoded() -> Result<(), Box<dyn std::error::Error>> {
    let big = "a".repeat(100_000);
    let port = origin(vec![("/", ok(&big))]).await?;
    let config = FetchConfig {
        max_bytes: 1_000,
        text_limit: 50_000,
        ..local()
    };
    let out = fetch(config, format!("http://127.0.0.1:{port}/")).await?;
    assert_eq!(out.text.len(), "HTTP 200\n".len() + 1_000);
    Ok(())
}
