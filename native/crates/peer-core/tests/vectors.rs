#![allow(clippy::pedantic)]
#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]

use nuxiva_peer_core::*;
use serde_json::{Value, json};
use std::path::PathBuf;

fn path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/locate.json")
}

fn outcome(directory: &mut Directory, verifier: &Verifier, env: &Envelope) -> String {
    match directory.learn(verifier, env, 0) {
        Ok(true) => "ok".to_owned(),
        Ok(false) => "stale".to_owned(),
        Err(e) => e.code().to_owned(),
    }
}

fn build() -> Value {
    let key = PeerKey::from_seed(&[5u8; 32]).expect("key");
    let stranger = PeerKey::from_seed(&[6u8; 32]).expect("key");
    let locate = |k: &PeerKey, seq: u64, addrs: &[&str]| {
        k.seal(
            seq,
            1_700_000_000_000,
            6,
            &Message::Locate {
                addrs: addrs.iter().map(|a| (*a).to_owned()).collect(),
            },
        )
        .expect("seal")
    };
    let valid = locate(&key, 4, &["192.168.1.20:7000", "nodo-1.local:7000"]);
    let mut tampered = valid.clone();
    tampered.payload = tampered.payload.replace("192.168.1.20", "192.168.1.99");
    let unknown = locate(&stranger, 1, &["10.0.0.5:7000"]);
    let wildcard = locate(&key, 5, &["0.0.0.0:7000"]);
    let empty = locate(&key, 6, &[]);
    let mut verifier_trust = TrustBook::new();
    verifier_trust.enroll(key.id()).expect("enroll");
    let verifier = Verifier::new(verifier_trust);
    let cases: Vec<(&str, Envelope)> = vec![
        ("valid", valid),
        ("tampered_payload", tampered),
        ("unknown_sender", unknown),
        ("wildcard_address", wildcard),
        ("empty_addresses", empty),
    ];
    let rows: Vec<Value> = cases
        .into_iter()
        .map(|(name, env)| {
            let expect = outcome(&mut Directory::new(), &verifier, &env);
            json!({"name": name, "envelope": env, "expect": expect})
        })
        .collect();
    json!({"trusted": [key.id()], "cases": rows})
}

#[test]
fn fixture_matches_and_verifies() {
    let fresh = build();
    if std::env::var("UPDATE_VECTORS").is_ok() {
        std::fs::write(path(), serde_json::to_string_pretty(&fresh).expect("json")).expect("write");
    }
    let stored: Value =
        serde_json::from_str(&std::fs::read_to_string(path()).expect("read")).expect("parse");
    assert_eq!(stored, fresh);
    let expected: Vec<&str> = stored["cases"]
        .as_array()
        .expect("cases")
        .iter()
        .map(|c| c["expect"].as_str().expect("e"))
        .collect();
    assert_eq!(expected[0], "ok");
    assert_eq!(expected[1], "peer.error.signature");
    assert_eq!(expected[2], "peer.error.untrusted");
    assert_eq!(expected[3], "peer.error.field");
    assert_eq!(expected[4], "peer.error.limit");
}
