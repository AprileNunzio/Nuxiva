use crate::hexutil;
use crate::identity::{fingerprint, verify_request};
use crate::signer::{DeviceKey, random_nonce};
use sha2::{Digest, Sha256};

fn digest(body: &[u8]) -> String {
    hexutil::encode(&Sha256::digest(body))
}

#[test]
fn generated_key_signs_and_server_verifies() {
    let key = DeviceKey::generate().expect("key");
    let signed = key
        .sign("pc-uno", "POST", "/api/nodes/heartbeat", b"{\"a\":1}", 5000)
        .expect("sign");
    assert!(
        verify_request(
            &key.public_hex(),
            &signed.signature,
            "pc-uno",
            "POST",
            "/api/nodes/heartbeat",
            signed.ts,
            &signed.nonce,
            &digest(b"{\"a\":1}"),
            5010
        )
        .is_ok()
    );
}

#[test]
fn body_path_and_node_are_bound() {
    let key = DeviceKey::generate().expect("key");
    let signed = key.sign("pc-uno", "POST", "/a", b"x", 5000).expect("sign");
    for (node, path, body) in [
        ("pc-due", "/a", &b"x"[..]),
        ("pc-uno", "/b", &b"x"[..]),
        ("pc-uno", "/a", &b"y"[..]),
    ] {
        assert!(
            verify_request(
                &key.public_hex(),
                &signed.signature,
                node,
                "POST",
                path,
                signed.ts,
                &signed.nonce,
                &digest(body),
                5000
            )
            .is_err()
        );
    }
}

#[test]
fn nonces_are_unique_and_long_enough() {
    let a = random_nonce().expect("nonce");
    let b = random_nonce().expect("nonce");
    assert_ne!(a, b);
    assert!(a.len() >= 16);
}

#[test]
fn seed_roundtrip_keeps_identity() {
    let key = DeviceKey::generate().expect("key");
    let again = DeviceKey::from_seed_hex(&key.seed_hex()).expect("seed");
    assert_eq!(key.public_hex(), again.public_hex());
    assert_eq!(key.pairing_code().expect("code").len(), 6);
    assert!(fingerprint(&key.public_hex()).is_ok());
}

#[test]
fn bad_seed_is_rejected() {
    assert!(DeviceKey::from_seed_hex("zz").is_err());
    assert!(DeviceKey::from_seed_hex(&"00".repeat(31)).is_err());
}

#[test]
fn debug_never_prints_the_seed() {
    let key = DeviceKey::from_seed(&[9u8; 32]).expect("key");
    assert!(!format!("{key:?}").contains(&*key.seed_hex()));
}

#[test]
fn deterministic_vector() {
    let key = DeviceKey::from_seed(&[7u8; 32]).expect("key");
    let signed = key
        .sign_at(
            "pc-uno",
            "POST",
            "/api/nodes/heartbeat",
            b"{}",
            1000,
            "0123456789abcdef0123",
        )
        .expect("sign");
    let vectors: serde_json::Value =
        serde_json::from_str(include_str!("../tests/signer_vectors.json")).expect("vectors");
    assert_eq!(vectors["public"], key.public_hex());
    assert_eq!(vectors["signature"], signed.signature);
}
