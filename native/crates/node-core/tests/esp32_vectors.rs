#![allow(clippy::expect_used, clippy::indexing_slicing, clippy::unwrap_used)]

use nuxiva_node_core::DeviceKey;
use nuxiva_node_core::identity;
use serde_json::Value;

fn vectors() -> Value {
    serde_json::from_str(include_str!("esp32_vectors.json")).expect("vectors")
}

#[test]
fn identity_vectors_match_the_firmware_contract() {
    for case in vectors()["identity"].as_array().expect("identity") {
        let key = DeviceKey::from_seed_hex(case["seed"].as_str().expect("seed")).expect("key");
        assert_eq!(key.public_hex(), case["public"].as_str().expect("public"));
        assert_eq!(
            key.pairing_code().expect("code"),
            case["pairing_code"].as_str().expect("code")
        );
        assert_eq!(
            identity::fingerprint(&key.public_hex()).expect("fingerprint"),
            case["fingerprint"].as_str().expect("fingerprint")
        );
    }
}

#[test]
fn signature_vectors_match_the_firmware_contract() {
    for case in vectors()["signatures"].as_array().expect("signatures") {
        let key = DeviceKey::from_seed_hex(case["seed"].as_str().expect("seed")).expect("key");
        let headers = key
            .sign_at(
                case["node"].as_str().expect("node"),
                case["method"].as_str().expect("method"),
                case["path"].as_str().expect("path"),
                case["body"].as_str().expect("body").as_bytes(),
                case["ts"].as_i64().expect("ts"),
                case["nonce"].as_str().expect("nonce"),
            )
            .expect("sign");
        assert_eq!(headers.signature, case["signature"].as_str().expect("sig"));
    }
}
