use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use hmac::{Hmac, Mac};
use serde_json::{Map, Value, json};
use sha2::Sha256;

use crate::{MAX_TOKEN, PREFIX, TokenCodec, TokenError, TokenResult};

const SECRET: &[u8] = b"0123456789abcdef0123456789abcdef";
const NOW: i64 = 1_800_000_000;

fn claims() -> Map<String, Value> {
    let mut map = Map::new();
    map.insert("role".into(), json!("OPERATOR"));
    map
}

fn codec() -> TokenResult<TokenCodec> {
    TokenCodec::new(SECRET)
}

fn reseal(payload: &Value) -> TokenResult<String> {
    let body = URL_SAFE_NO_PAD.encode(payload.to_string());
    let mut mac = Hmac::<Sha256>::new_from_slice(SECRET).map_err(|_| TokenError::WeakSecret)?;
    mac.update(body.as_bytes());
    let signature = URL_SAFE_NO_PAD.encode(mac.finalize().into_bytes());
    Ok(format!("{PREFIX}{body}.{signature}"))
}

#[test]
fn round_trip_keeps_subject_and_claims() -> TokenResult<()> {
    let codec = codec()?;
    let token = codec.issue("tablet-1", claims(), NOW, 3600)?;
    let payload = codec.verify(&token, NOW + 10)?;
    assert_eq!(payload.sub, "tablet-1");
    assert_eq!(payload.exp, NOW + 3600);
    assert_eq!(payload.claims.get("role"), Some(&json!("OPERATOR")));
    Ok(())
}

#[test]
fn weak_secrets_are_refused() {
    assert_eq!(
        TokenCodec::new(b"short").err(),
        Some(TokenError::WeakSecret)
    );
    assert_eq!(
        TokenCodec::new(&[0_u8; 32]).err(),
        Some(TokenError::WeakSecret)
    );
    assert_eq!(
        TokenCodec::new(&[7_u8; 64]).err(),
        Some(TokenError::WeakSecret)
    );
}

#[test]
fn tampered_payload_or_signature_fails() -> TokenResult<()> {
    let codec = codec()?;
    let token = codec.issue("tablet-1", claims(), NOW, 3600)?;
    let forged = token.replacen(PREFIX, &format!("{PREFIX}A"), 1);
    assert!(codec.verify(&forged, NOW).is_err());
    let mut chars: Vec<char> = token.chars().collect();
    if let Some(last) = chars.last_mut() {
        *last = if *last == 'A' { 'B' } else { 'A' };
    }
    let flipped: String = chars.into_iter().collect();
    assert!(codec.verify(&flipped, NOW).is_err());
    let other = TokenCodec::new(b"fedcba9876543210fedcba9876543210")?;
    assert_eq!(other.verify(&token, NOW), Err(TokenError::Signature));
    Ok(())
}

#[test]
fn expiry_and_future_tokens_are_rejected() -> TokenResult<()> {
    let codec = codec()?;
    let token = codec.issue("tablet-1", claims(), NOW, 60)?;
    assert!(codec.verify(&token, NOW + 60).is_ok());
    assert_eq!(codec.verify(&token, NOW + 61), Err(TokenError::Expired));
    assert_eq!(
        codec.verify(&token, NOW - 120),
        Err(TokenError::NotYetValid)
    );
    Ok(())
}

#[test]
fn malformed_tokens_are_format_errors() -> TokenResult<()> {
    let codec = codec()?;
    for token in [
        "",
        "v1.local.",
        "v2.local.a.b",
        "v1.local.abc",
        "v1.local.a.b.c",
        "v1.local.a==.bbbb",
    ] {
        assert_eq!(codec.verify(token, NOW), Err(TokenError::Format), "{token}");
    }
    assert_eq!(
        codec.verify(&"a".repeat(MAX_TOKEN + 1), NOW),
        Err(TokenError::TooLarge)
    );
    Ok(())
}

#[test]
fn signed_but_invalid_payloads_are_refused() -> TokenResult<()> {
    let codec = codec()?;
    for payload in [
        json!({"sub": "a", "iat": NOW, "exp": NOW + 5}),
        json!({"sub": "a", "iat": NOW, "exp": NOW + 5, "claims": {}, "admin": true}),
        json!({"sub": "", "iat": NOW, "exp": NOW + 5, "claims": {}}),
        json!({"sub": "a\u{0}", "iat": NOW, "exp": NOW + 5, "claims": {}}),
        json!({"sub": "a", "iat": NOW, "exp": NOW - 5, "claims": {}}),
        json!(["sub"]),
    ] {
        assert!(codec.verify(&reseal(&payload)?, NOW).is_err(), "{payload}");
    }
    Ok(())
}

#[test]
fn issue_validates_inputs() -> TokenResult<()> {
    let codec = codec()?;
    assert_eq!(
        codec.issue("", claims(), NOW, 60).err(),
        Some(TokenError::Subject)
    );
    assert_eq!(
        codec.issue("a", claims(), NOW, 0).err(),
        Some(TokenError::Lifetime)
    );
    assert_eq!(
        codec.issue("a", claims(), i64::MAX, 60).err(),
        Some(TokenError::Lifetime)
    );
    let mut big = Map::new();
    big.insert("blob".into(), json!("x".repeat(5000)));
    assert_eq!(
        codec.issue("a", big, NOW, 60).err(),
        Some(TokenError::Claims)
    );
    Ok(())
}

#[test]
fn debug_never_prints_the_secret() -> TokenResult<()> {
    let rendered = format!("{:?}", codec()?);
    assert!(!rendered.contains("0123456789abcdef"));
    Ok(())
}
