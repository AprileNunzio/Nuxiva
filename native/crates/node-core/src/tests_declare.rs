use crate::announce;
use crate::declare::{Facts, declare, scopes};
use crate::profile::{Ceiling, Mode, Profile, resolve};

fn board() -> Facts {
    Facts {
        microphone: true,
        speaker: true,
        camera: false,
        sensors: true,
        display: false,
        edge_inference: true,
        cpu_cores: 8,
        ram_mb: 16384,
    }
}

#[test]
fn satellite_declaration_is_accepted_and_stays_in_the_satellite_set() {
    let parsed = announce::parse(&declare(&board(), false).to_string()).expect("parse");
    assert!(parsed.rejected.is_empty());
    assert!(!parsed.full_host);
    assert_eq!(
        parsed.scopes,
        [
            "audio.capture",
            "audio.play",
            "inference.edge",
            "sensor.read",
            "telemetry.report"
        ]
    );
}

#[test]
fn host_declaration_enables_second_server_only_with_consent_and_hardware() {
    let parsed = announce::parse(&declare(&board(), true).to_string()).expect("parse");
    assert!(parsed.full_host);
    assert!(parsed.rejected.is_empty());
    let allowed = Ceiling {
        second_server: true,
    };
    let denied = Ceiling {
        second_server: false,
    };
    assert_eq!(
        resolve(
            Profile::parse("second_server"),
            &parsed.hardware,
            true,
            allowed
        ),
        Mode::SecondServer
    );
    assert_eq!(
        resolve(
            Profile::parse("second_server"),
            &parsed.hardware,
            true,
            denied
        ),
        Mode::Satellite
    );
    let weak = Facts {
        cpu_cores: 1,
        ram_mb: 512,
        ..board()
    };
    let weak = announce::parse(&declare(&weak, true).to_string()).expect("parse");
    assert_eq!(
        resolve(Profile::parse("auto"), &weak.hardware, true, allowed),
        Mode::Satellite
    );
}

#[test]
fn declaration_never_carries_elevated_or_forbidden_scopes() {
    for host in [false, true] {
        for scope in scopes(&Facts::default(), host) {
            assert!(!crate::scope::forbidden(&scope));
            assert!(!crate::scope::elevated(&scope));
        }
    }
}

#[test]
fn vectors_are_shared_with_python() {
    let vectors: serde_json::Value =
        serde_json::from_str(include_str!("../tests/declare_vectors.json")).expect("vectors");
    for case in vectors.as_array().expect("cases") {
        let f = &case["facts"];
        let facts = Facts {
            microphone: f["microphone"].as_bool().expect("b"),
            speaker: f["speaker"].as_bool().expect("b"),
            camera: f["camera"].as_bool().expect("b"),
            sensors: f["sensors"].as_bool().expect("b"),
            display: f["display"].as_bool().expect("b"),
            edge_inference: f["edge_inference"].as_bool().expect("b"),
            cpu_cores: u32::try_from(f["cpu_cores"].as_u64().expect("n")).expect("u32"),
            ram_mb: f["ram_mb"].as_u64().expect("n"),
        };
        assert_eq!(
            declare(&facts, case["host_full"].as_bool().expect("b")),
            case["expect"],
            "{case}"
        );
    }
}
