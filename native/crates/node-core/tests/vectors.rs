#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::unwrap_used,
    clippy::too_many_lines,
    clippy::panic
)]

use nuxiva_node_core::announce;
use nuxiva_node_core::audit::{self, Entry};
use nuxiva_node_core::authorize::{Verdict, authorize, effective};
use nuxiva_node_core::identity;
use nuxiva_node_core::profile::{Ceiling, Mode, Profile, resolve};
use serde_json::Value;

fn vectors() -> Value {
    serde_json::from_str(include_str!("vectors.json")).expect("vectors")
}

fn strings(value: &Value) -> Vec<String> {
    value
        .as_array()
        .expect("array")
        .iter()
        .map(|v| v.as_str().expect("str").to_owned())
        .collect()
}

#[test]
fn mode_vectors() {
    for case in vectors()["mode"].as_array().expect("mode") {
        let a = case["args"].as_array().expect("args");
        let hardware = announce::Hardware {
            cpu_cores: u32::try_from(a[1].as_u64().expect("cores")).expect("u32"),
            ram_mb: a[2].as_u64().expect("ram"),
        };
        let mode = resolve(
            Profile::parse(a[0].as_str().expect("profile")),
            &hardware,
            a[3].as_bool().expect("full"),
            Ceiling {
                second_server: a[4].as_bool().expect("allowed"),
            },
        );
        assert_eq!(
            mode.as_str(),
            case["expect"].as_str().expect("expect"),
            "{case}"
        );
    }
}

#[test]
fn effective_vectors() {
    for case in vectors()["effective"].as_array().expect("effective") {
        let a = case["args"].as_array().expect("args");
        let mode = if a[0].as_str() == Some("second_server") {
            Mode::SecondServer
        } else {
            Mode::Satellite
        };
        assert_eq!(
            effective(mode, &strings(&a[1]), &strings(&a[2])),
            strings(&case["expect"]),
            "{case}"
        );
    }
}

#[test]
fn authorize_vectors() {
    for case in vectors()["authorize"].as_array().expect("authorize") {
        let a = case["args"].as_array().expect("args");
        let verdict = authorize(&strings(&a[0]), a[1].as_str().expect("requested"));
        let expect = case["expect"].as_array().expect("expect");
        match verdict {
            Verdict::Allow => assert_eq!(expect[0].as_bool(), Some(true), "{case}"),
            Verdict::Deny(code) => {
                assert_eq!(expect[0].as_bool(), Some(false), "{case}");
                assert_eq!(expect[1].as_str(), Some(code), "{case}");
            }
        }
    }
}

#[test]
fn announce_vectors() {
    for case in vectors()["announce"].as_array().expect("announce") {
        let raw = case["raw"].as_str().expect("raw");
        let expect = &case["expect"];
        match announce::parse(raw) {
            Ok(parsed) => {
                let ok = &expect["ok"];
                assert!(
                    ok.is_object(),
                    "rust accepted {raw:.80} python said {expect}"
                );
                assert_eq!(strings(&ok["scopes"]), parsed.scopes, "{raw:.60}");
                assert_eq!(strings(&ok["rejected"]), parsed.rejected, "{raw:.60}");
                assert_eq!(
                    ok["cpu_cores"].as_u64(),
                    Some(u64::from(parsed.hardware.cpu_cores)),
                    "{raw:.60}"
                );
                assert_eq!(
                    ok["ram_mb"].as_u64(),
                    Some(parsed.hardware.ram_mb),
                    "{raw:.60}"
                );
                assert_eq!(
                    ok["full_host"].as_bool(),
                    Some(parsed.full_host),
                    "{raw:.60}"
                );
            }
            Err(error) => assert_eq!(expect["error"].as_str(), Some(error.code()), "{raw:.60}"),
        }
    }
}

#[test]
fn identity_vectors() {
    let v = vectors();
    let one = v["keys"]["one"].as_str().expect("one");
    let two = v["keys"]["two"].as_str().expect("two");
    let id = &v["identity"];
    assert_eq!(
        identity::fingerprint(one).expect("fp"),
        id["fingerprint"].as_str().expect("s")
    );
    assert_eq!(
        identity::pairing_code(one).expect("code"),
        id["code"].as_str().expect("s")
    );
    assert_eq!(
        identity::fingerprint(two).expect("fp"),
        id["fingerprint_two"].as_str().expect("s")
    );
    assert_eq!(
        identity::pairing_code(two).expect("code"),
        id["code_two"].as_str().expect("s")
    );
}

#[test]
fn verify_vectors() {
    for case in vectors()["verify"].as_array().expect("verify") {
        let a = case["args"].as_array().expect("args");
        let s = |i: usize| a[i].as_str().expect("str");
        let result = identity::verify_request(
            s(0),
            s(1),
            s(2),
            s(3),
            s(4),
            a[5].as_i64().expect("ts"),
            s(6),
            s(7),
            a[8].as_i64().expect("now"),
        );
        match (&case["expect"]["ok"], result) {
            (Value::Bool(true), Ok(())) => {}
            (Value::Null, Err(error)) => {
                assert_eq!(
                    case["expect"]["error"].as_str(),
                    Some(error.code()),
                    "{}",
                    case["name"]
                );
            }
            (_, other) => panic!("{} {:?}", case["name"], other),
        }
    }
}

#[test]
fn audit_vectors() {
    let v = vectors();
    for case in v["audit_seal"].as_array().expect("seal") {
        let a = case["args"].as_array().expect("args");
        let s = |i: usize| a[i].as_str().expect("str");
        let sealed = audit::seal(
            s(0),
            a[1].as_u64().expect("seq"),
            a[2].as_i64().expect("ts"),
            s(3),
            s(4),
            s(5),
            s(6),
        );
        let expected: Entry = serde_json::from_value(case["expect"].clone()).expect("entry");
        assert_eq!(sealed, expected);
    }
    for case in v["audit_verify"].as_array().expect("verify") {
        let entries: Vec<Entry> = serde_json::from_value(case["entries"].clone()).expect("entries");
        let got = audit::verify_chain(case["anchor"].as_str().expect("anchor"), &entries);
        let expect = case["expect"].as_i64().expect("expect");
        assert_eq!(got.map_or(-1, |i| i64::try_from(i).expect("i64")), expect);
    }
}
