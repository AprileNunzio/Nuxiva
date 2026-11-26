use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use model_fit::Quant;

use crate::reply::{parse_chat, parse_images, parse_models};
use crate::{
    ApiKey, Capabilities, Capability, ChatRequest, Endpoint, ImageRequest, ImageSize, Media,
    MediaKind, Message, Precision, Role, SpeechFormat, SpeechRequest, StudioError, clean_text,
    parse_precision, sniff, valid_id,
};

const PNG: &[u8] = b"\x89PNG\r\n\x1a\n0000";

fn chat(content: &str) -> ChatRequest {
    ChatRequest {
        model: "org/model-27b-GGUF".into(),
        messages: vec![Message {
            role: Role::User,
            content: content.into(),
        }],
        max_tokens: 256,
        temperature_milli: Some(700),
        thinking: true,
    }
}

#[test]
fn endpoint_requires_tls_outside_private_networks() {
    assert!(Endpoint::parse("http://127.0.0.1:8888").is_ok());
    assert!(Endpoint::parse("http://192.168.1.20:8888/v1").is_ok());
    assert!(Endpoint::parse("http://100.90.1.2:8888").is_ok());
    assert!(Endpoint::parse("http://[fd00::5]:8888").is_ok());
    assert!(Endpoint::parse("http://localhost:8000").is_ok());
    assert!(Endpoint::parse("https://studio.example.org").is_ok());
    assert_eq!(
        Endpoint::parse("http://8.8.8.8:8888").err(),
        Some(StudioError::Insecure)
    );
    assert_eq!(
        Endpoint::parse("http://studio.example.org").err(),
        Some(StudioError::Insecure)
    );
}

#[test]
fn endpoint_rejects_credentials_queries_and_odd_schemes() {
    for bad in [
        "http://user:pw@127.0.0.1:8888",
        "http://127.0.0.1:8888/?x=1",
        "http://127.0.0.1:8888/#f",
        "ftp://127.0.0.1",
        "http://0.0.0.0:8888",
        "",
    ] {
        assert!(Endpoint::parse(bad).is_err(), "{bad}");
    }
}

#[test]
fn endpoint_joins_only_allowlisted_paths() {
    let endpoint = Endpoint::parse("http://127.0.0.1:8888/v1/").expect("endpoint");
    let url = endpoint.join("v1/chat/completions").expect("join");
    assert_eq!(url.as_str(), "http://127.0.0.1:8888/v1/chat/completions");
    assert!(endpoint.join("v1/../admin").is_err());
    assert!(endpoint.join("v1/audio/run").is_err());
}

#[test]
fn api_key_is_validated_and_never_printed() {
    let key = ApiKey::new("sk-abcdefghijklmnop1234").expect("key");
    assert_eq!(format!("{key:?}"), "ApiKey(***)");
    assert!(ApiKey::new("short").is_err());
    assert!(ApiKey::new("sk-abcdefghijklmnop\r\nX: y").is_err());
}

#[test]
fn text_is_cleaned_of_controls_and_hidden_marks() {
    let cleaned = clean_text("  ciao\u{202e}\u{0007} mondo\n ", 100, "x").expect("clean");
    assert_eq!(cleaned, "ciao mondo");
    assert_eq!(
        clean_text("\u{200b}", 10, "x").err(),
        Some(StudioError::Invalid("x"))
    );
    assert_eq!(
        clean_text("abcdef", 3, "x").err(),
        Some(StudioError::TooLarge)
    );
    assert!(valid_id("org/model-7b:q4"));
    assert!(!valid_id("../etc"));
    assert!(!valid_id("a b"));
}

#[test]
fn chat_body_always_disables_server_tools_and_streaming() {
    let body = chat("Scrivi una poesia").to_json().expect("json");
    assert_eq!(body["enable_tools"], false);
    assert_eq!(body["stream"], false);
    assert_eq!(body["enable_thinking"], true);
    assert_eq!(body["messages"][0]["role"], "user");
    assert!((body["temperature"].as_f64().expect("t") - 0.7).abs() < 1e-9);
}

#[test]
fn chat_limits_are_enforced() {
    let mut request = chat("x");
    request.max_tokens = 0;
    assert!(request.to_json().is_err());
    let mut request = chat("x");
    request.temperature_milli = Some(5000);
    assert!(request.to_json().is_err());
    let mut request = chat("x");
    request.messages.clear();
    assert!(request.to_json().is_err());
    let mut request = chat("x");
    request.model = "bad model".into();
    assert_eq!(request.to_json().err(), Some(StudioError::Invalid("model")));
}

#[test]
fn image_and_speech_bodies_are_bounded() {
    let image = ImageRequest {
        model: "m".into(),
        prompt: "un faro".into(),
        size: ImageSize::Wide,
        count: 2,
    };
    let body = image.to_json().expect("json");
    assert_eq!(body["size"], "1344x768");
    assert_eq!(body["response_format"], "b64_json");
    assert!(ImageRequest { count: 9, ..image }.to_json().is_err());
    let speech = SpeechRequest {
        model: "tts".into(),
        input: "Buonasera".into(),
        voice: "it-1".into(),
        format: SpeechFormat::Wav,
    };
    assert_eq!(speech.to_json().expect("json")["response_format"], "wav");
}

#[test]
fn precision_tags_map_to_memory_planning() {
    assert_eq!(parse_precision("UD-Q4_K_XL"), Some(Precision::Q4));
    assert_eq!(
        parse_precision("model-27b-UD-IQ1_S.gguf"),
        Some(Precision::Q1)
    );
    assert_eq!(parse_precision("org/model-GGUF:Q8_0"), Some(Precision::Q8));
    assert_eq!(parse_precision("model-BF16.gguf"), Some(Precision::F16));
    assert_eq!(parse_precision("model-MXFP4"), Some(Precision::Q4));
    assert_eq!(parse_precision("model-Q3_K_M"), Some(Precision::Q3));
    assert_eq!(parse_precision("plain-model"), None);
    assert_eq!(Precision::Q4.to_fit(), Some(Quant::Q4));
    assert_eq!(Precision::Q1.to_fit(), None);
    assert!(!Precision::Q1.agentic_ok());
    assert!(Precision::Q2.agentic_ok());
}

#[test]
fn media_is_recognised_by_content_not_by_label() {
    assert_eq!(sniff(PNG), Some(MediaKind::Png));
    assert_eq!(sniff(b"\xff\xd8\xff\xe0"), Some(MediaKind::Jpeg));
    assert_eq!(sniff(b"RIFF\0\0\0\0WAVEfmt "), Some(MediaKind::Wav));
    assert_eq!(sniff(b"RIFF\0\0\0\0WEBPVP8 "), Some(MediaKind::Webp));
    assert_eq!(sniff(b"ID3\x04"), Some(MediaKind::Mp3));
    assert_eq!(sniff(b"<html>"), None);
    assert!(Media::from_bytes(b"<script>".to_vec(), 100).is_err());
    assert_eq!(
        Media::from_bytes(PNG.to_vec(), 4).err(),
        Some(StudioError::TooLarge)
    );
}

#[test]
fn capabilities_come_only_from_declared_post_routes() {
    let schema = r#"{"paths":{"/v1/chat/completions":{"post":{}},"/v1/images/generations":{"get":{}},"/v1/audio/speech":{"post":{}}}}"#;
    let caps = Capabilities::from_openapi(schema).expect("caps");
    assert!(caps.has(Capability::Chat));
    assert!(!caps.has(Capability::Image));
    assert!(caps.has(Capability::Speech));
    assert_eq!(caps.keys(), vec!["chat", "speech"]);
    assert_eq!(
        caps.require(Capability::Image).err(),
        Some(StudioError::Unsupported("image"))
    );
    assert!(Capabilities::from_openapi("{}").is_err());
}

#[test]
fn replies_are_parsed_defensively() {
    let reply = parse_chat(r#"{"choices":[{"message":{"content":"ok\u0007","reasoning_content":"think"},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":2}}"#).expect("chat");
    assert_eq!(reply.text, "ok");
    assert_eq!(reply.reasoning.as_deref(), Some("think"));
    assert_eq!(reply.usage.completion_tokens, 2);
    assert!(parse_chat(r#"{"choices":[]}"#).is_err());
    assert!(parse_chat(r#"{"choices":[{"message":{"content":""}}]}"#).is_err());
    let models = parse_models(r#"{"data":[{"id":"org/a-GGUF","loaded":true},{"id":"../x"}]}"#)
        .expect("models");
    assert_eq!(models.len(), 1);
    assert_eq!(models[0].loaded, Some(true));
    let encoded = STANDARD.encode(PNG);
    let images =
        parse_images(&format!(r#"{{"data":[{{"b64_json":"{encoded}"}}]}}"#), 1024).expect("images");
    assert_eq!(images[0].kind, MediaKind::Png);
    let wav = STANDARD.encode(b"RIFF\0\0\0\0WAVEfmt ");
    assert!(parse_images(&format!(r#"{{"data":[{{"b64_json":"{wav}"}}]}}"#), 1024).is_err());
}
