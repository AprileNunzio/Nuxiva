use std::time::Duration;

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tokio::task::JoinHandle;

use crate::{
    ApiKey, Capability, ChatRequest, Endpoint, Limits, Message, Role, SpeechFormat, SpeechRequest,
    StudioClient, StudioError,
};

const KEY: &str = "sk-test-0123456789abcdef";

async fn serve(responses: Vec<Vec<u8>>) -> (String, JoinHandle<Vec<String>>) {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let address = listener.local_addr().expect("addr");
    let task = tokio::spawn(async move {
        let mut seen = Vec::new();
        for response in responses {
            let Ok((mut socket, _)) = listener.accept().await else {
                break;
            };
            let mut buffer = vec![0_u8; 16_384];
            let read = socket.read(&mut buffer).await.unwrap_or(0);
            seen.push(String::from_utf8_lossy(&buffer[..read]).into_owned());
            let _ = socket.write_all(&response).await;
            let _ = socket.shutdown().await;
        }
        seen
    });
    (format!("http://{address}"), task)
}

fn http(status: &str, kind: &str, body: &[u8]) -> Vec<u8> {
    let mut out = format!(
        "HTTP/1.1 {status}\r\nContent-Type: {kind}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    )
    .into_bytes();
    out.extend_from_slice(body);
    out
}

fn client(base: &str, limits: Limits) -> StudioClient {
    let key = ApiKey::new(KEY).expect("key");
    StudioClient::new(Endpoint::parse(base).expect("endpoint"), key, limits).expect("client")
}

fn limits() -> Limits {
    Limits {
        timeout: Duration::from_secs(5),
        connect: Duration::from_secs(2),
        max_json: 4096,
        max_media: 4096,
    }
}

const SCHEMA: &str =
    r#"{"paths":{"/v1/chat/completions":{"post":{}},"/v1/audio/speech":{"post":{}}}}"#;

#[tokio::test]
async fn discovers_then_chats_with_bearer_and_tools_off() {
    let chat = r#"{"choices":[{"message":{"content":"ciao"},"finish_reason":"stop"}]}"#;
    let (base, task) = serve(vec![
        http("200 OK", "application/json", SCHEMA.as_bytes()),
        http("200 OK", "application/json", chat.as_bytes()),
    ])
    .await;
    let mut studio = client(&base, limits());
    let caps = studio.discover().await.expect("discover");
    assert!(caps.has(Capability::Chat) && !caps.has(Capability::Image));
    let request = ChatRequest {
        model: "org/m".into(),
        messages: vec![Message {
            role: Role::User,
            content: "ciao".into(),
        }],
        max_tokens: 32,
        temperature_milli: None,
        thinking: false,
    };
    let reply = studio.chat(&request).await.expect("chat");
    assert_eq!(reply.text, "ciao");
    let seen = task.await.expect("seen");
    assert!(seen[0].starts_with("GET /openapi.json"));
    assert!(seen[1].starts_with("POST /v1/chat/completions"));
    assert!(
        seen[1]
            .to_ascii_lowercase()
            .contains(&format!("authorization: bearer {KEY}"))
    );
    assert!(seen[1].contains(r#""enable_tools":false"#));
}

#[tokio::test]
async fn undeclared_capabilities_are_refused_without_network() {
    let studio = client("http://127.0.0.1:9", limits());
    let request = ChatRequest {
        model: "m".into(),
        messages: vec![Message {
            role: Role::User,
            content: "x".into(),
        }],
        max_tokens: 1,
        temperature_milli: None,
        thinking: false,
    };
    assert_eq!(
        studio.chat(&request).await.err(),
        Some(StudioError::Unsupported("chat"))
    );
}

#[tokio::test]
async fn speech_accepts_binary_audio_and_rejects_other_content() {
    let wav = b"RIFF\0\0\0\0WAVEfmt data";
    let (base, _task) = serve(vec![
        http("200 OK", "application/json", SCHEMA.as_bytes()),
        http("200 OK", "audio/wav", wav),
        http("200 OK", "audio/wav", b"<html>"),
    ])
    .await;
    let mut studio = client(&base, limits());
    studio.discover().await.expect("discover");
    let request = SpeechRequest {
        model: "tts".into(),
        input: "Buonasera".into(),
        voice: "v1".into(),
        format: SpeechFormat::Wav,
    };
    let audio = studio.speech(&request).await.expect("speech");
    assert_eq!(audio.bytes, wav);
    assert_eq!(
        studio.speech(&request).await.err(),
        Some(StudioError::Malformed("media"))
    );
}

#[tokio::test]
async fn statuses_and_oversized_bodies_are_reported() {
    let big = vec![b'a'; 8192];
    let (base, _task) = serve(vec![
        http("401 Unauthorized", "application/json", b"{}"),
        http("429 Too Many Requests", "application/json", b"{}"),
        http("200 OK", "application/json", &big),
        http("500 Internal Server Error", "application/json", b"{}"),
    ])
    .await;
    let studio = client(&base, limits());
    assert_eq!(studio.models().await.err(), Some(StudioError::Auth));
    assert_eq!(studio.models().await.err(), Some(StudioError::Busy));
    assert_eq!(studio.models().await.err(), Some(StudioError::TooLarge));
    assert_eq!(
        studio.models().await.err(),
        Some(StudioError::Upstream(500))
    );
}

#[tokio::test]
async fn missing_schema_falls_back_to_chat_after_listing_models() {
    let (base, _task) = serve(vec![
        http("404 Not Found", "application/json", b"{}"),
        http(
            "200 OK",
            "application/json",
            br#"{"data":[{"id":"org/m"}]}"#,
        ),
    ])
    .await;
    let mut studio = client(&base, limits());
    let caps = studio.discover().await.expect("discover");
    assert_eq!(caps.keys(), vec!["chat"]);
}
