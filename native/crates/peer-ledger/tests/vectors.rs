#![allow(clippy::pedantic)]
#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]

use nuxiva_peer_core::{PeerKey, TrustBook};
use nuxiva_peer_ledger::block::GENESIS;
use nuxiva_peer_ledger::{Block, Ledger, Wire};
use serde_json::{Value, json};
use std::path::PathBuf;

const NOW: i64 = 1_700_000_000_000;

fn path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/ledger.json")
}

fn key(n: u8) -> PeerKey {
    PeerKey::from_seed(&[n; 32]).expect("key")
}

fn addrs(n: u8) -> Vec<String> {
    vec![
        format!("192.168.1.{n}:8443"),
        format!("nodo-{n}.local:8443"),
    ]
}

fn forged(key: &PeerKey, index: u64, prev: &str, ts: i64, list: Vec<String>) -> Block {
    let sig = key.sign(&Block::signed_bytes(key.id(), index, prev, ts, &list));
    Block {
        author: key.id().to_owned(),
        index,
        prev: prev.to_owned(),
        ts,
        addrs: list,
        sig,
    }
}

fn verdict(result: Result<bool, nuxiva_peer_ledger::LedgerError>) -> String {
    match result {
        Ok(true) => "new".to_owned(),
        Ok(false) => "known".to_owned(),
        Err(error) => error.code().to_owned(),
    }
}

fn build() -> Value {
    let (a, stranger) = (key(1), key(2));
    let b0 = Block::seal(&a, 0, GENESIS, NOW, addrs(10)).expect("seal");
    let b1 = Block::seal(&a, 1, &b0.hash(), NOW + 1000, addrs(11)).expect("seal");
    let b2 = Block::seal(&a, 2, &b1.hash(), NOW + 2000, addrs(12)).expect("seal");
    let fork = Block::seal(&a, 1, &b0.hash(), NOW + 1000, addrs(99)).expect("seal");
    let mut tampered = b2.clone();
    tampered.addrs = addrs(77);
    let foreign = Block::seal(&stranger, 0, GENESIS, NOW, addrs(10)).expect("seal");
    let future = forged(&a, 3, &b2.hash(), NOW + 500_000, addrs(13));
    let wrong_link = forged(&a, 3, GENESIS, NOW + 3000, addrs(13));
    let backwards = forged(&a, 3, &b2.hash(), NOW, addrs(13));
    let wildcard = forged(
        &a,
        3,
        &b2.hash(),
        NOW + 3000,
        vec!["0.0.0.0:7000".to_owned()],
    );
    let steps: Vec<(&str, &Block)> = vec![
        ("first", &b0),
        ("repeat", &b0),
        ("gap", &b2),
        ("second", &b1),
        ("fork", &fork),
        ("third", &b2),
        ("tampered", &tampered),
        ("unknown_author", &foreign),
        ("future_clock", &future),
        ("wrong_link", &wrong_link),
        ("clock_backwards", &backwards),
        ("wildcard_address", &wildcard),
    ];
    let mut trust = TrustBook::new();
    trust.enroll(a.id()).expect("enroll");
    let mut ledger = Ledger::new(trust);
    let rows: Vec<Value> = steps
        .into_iter()
        .map(|(name, block)| {
            let expect = verdict(ledger.accept(block.clone(), NOW));
            json!({"name": name, "block": block, "hash": block.hash(), "expect": expect})
        })
        .collect();
    let want = Wire::Want {
        id: a.id().to_owned(),
    };
    let have = ledger.answer(&want).expect("have");
    let empty = Ledger::new({
        let mut t = TrustBook::new();
        t.enroll(a.id()).expect("enroll");
        t
    });
    let delta = ledger.answer(&empty.digest_request()).expect("delta");
    let wires: Vec<Value> = vec![
        (
            "want",
            String::from_utf8(want.encode().expect("e")).expect("u"),
        ),
        (
            "have",
            String::from_utf8(have.encode().expect("e")).expect("u"),
        ),
        (
            "delta",
            String::from_utf8(delta.encode().expect("e")).expect("u"),
        ),
        ("bad_field", "{\"t\":\"want\",\"id\":\"zz\"}".to_owned()),
        (
            "unknown_field",
            format!("{{\"t\":\"want\",\"id\":\"{}\",\"x\":1}}", a.id()),
        ),
    ]
    .into_iter()
    .map(|(name, raw)| {
        let expect = match Wire::decode(raw.as_bytes()) {
            Ok(_) => "ok".to_owned(),
            Err(error) => error.code().to_owned(),
        };
        json!({"name": name, "raw": raw, "expect": expect})
    })
    .collect();
    json!({
        "now": NOW,
        "trusted": [a.id()],
        "steps": rows,
        "heads": ledger.digest(),
        "candidates": ledger.candidates(a.id()),
        "wires": wires,
    })
}

#[test]
fn fixture_matches() {
    let fresh = build();
    if std::env::var("UPDATE_VECTORS").is_ok() {
        std::fs::write(path(), serde_json::to_string_pretty(&fresh).expect("json")).expect("write");
    }
    let stored: Value =
        serde_json::from_str(&std::fs::read_to_string(path()).expect("read")).expect("parse");
    assert_eq!(stored, fresh);
    let expect: Vec<&str> = stored["steps"]
        .as_array()
        .expect("steps")
        .iter()
        .map(|s| s["expect"].as_str().expect("e"))
        .collect();
    assert_eq!(
        expect,
        [
            "new",
            "known",
            "ledger.error.gap",
            "new",
            "ledger.error.fork",
            "new",
            "ledger.error.signature",
            "ledger.error.untrusted",
            "ledger.error.clock",
            "ledger.error.link",
            "ledger.error.clock",
            "ledger.error.field",
        ]
    );
}
