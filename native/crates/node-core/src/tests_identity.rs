use crate::hexutil;
use crate::identity::{canonical, fingerprint, pairing_code, verify_request};
use ed25519_dalek::{Signer, SigningKey};
use sha2::{Digest, Sha256};

const NONCE: &str = "0123456789abcdef0123";

fn key() -> SigningKey {
    SigningKey::from_bytes(&[7u8; 32])
}

fn public(k: &SigningKey) -> String {
    hexutil::encode(k.verifying_key().as_bytes())
}

fn body_hash(body: &[u8]) -> String {
    hexutil::encode(&Sha256::digest(body))
}

fn signed(k: &SigningKey, path: &str, ts: i64, body: &[u8]) -> String {
    let message =
        canonical("pc-uno", "POST", path, ts, NONCE, &body_hash(body)).expect("canonical");
    hexutil::encode(&k.sign(&message).to_bytes())
}

#[test]
fn valid_signature_passes() {
    let k = key();
    let sig = signed(&k, "/api/nodes/heartbeat", 1000, b"{}");
    assert!(
        verify_request(
            &public(&k),
            &sig,
            "pc-uno",
            "POST",
            "/api/nodes/heartbeat",
            1000,
            NONCE,
            &body_hash(b"{}"),
            1010
        )
        .is_ok()
    );
}

#[test]
fn tampered_fields_fail() {
    let k = key();
    let sig = signed(&k, "/api/nodes/heartbeat", 1000, b"{}");
    let pk = public(&k);
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-due",
            "POST",
            "/api/nodes/heartbeat",
            1000,
            NONCE,
            &body_hash(b"{}"),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/api/nodes/other",
            1000,
            NONCE,
            &body_hash(b"{}"),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/api/nodes/heartbeat",
            1000,
            NONCE,
            &body_hash(b"{x}"),
            1000
        )
        .is_err()
    );
}

#[test]
fn clock_skew_rejected() {
    let k = key();
    let sig = signed(&k, "/p", 1000, b"");
    let pk = public(&k);
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1061
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            939
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1060
        )
        .is_ok()
    );
}

#[test]
fn wrong_key_rejected() {
    let k = key();
    let other = SigningKey::from_bytes(&[9u8; 32]);
    let sig = signed(&k, "/p", 1000, b"");
    assert!(
        verify_request(
            &public(&other),
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1000
        )
        .is_err()
    );
}

#[test]
fn malformed_inputs_rejected() {
    let k = key();
    let sig = signed(&k, "/p", 1000, b"");
    let pk = public(&k);
    assert!(
        verify_request(
            "zz",
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            "abcd",
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "post",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/p\nx",
            1000,
            NONCE,
            &body_hash(b""),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &pk,
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            "short",
            &body_hash(b""),
            1000
        )
        .is_err()
    );
    assert!(
        verify_request(
            &"00".repeat(32),
            &sig,
            "pc-uno",
            "POST",
            "/p",
            1000,
            NONCE,
            &body_hash(b""),
            1000
        )
        .is_err()
    );
}

#[test]
fn fingerprint_is_stable_and_formatted() {
    let pk = public(&key());
    let one = fingerprint(&pk).expect("fp");
    assert_eq!(one, fingerprint(&pk).expect("fp"));
    assert_eq!(one.len(), 14);
    assert_eq!(one.matches('-').count(), 2);
    let code = pairing_code(&pk).expect("code");
    assert_eq!(code.len(), 6);
    assert!(code.bytes().all(|b| b.is_ascii_digit()));
}
