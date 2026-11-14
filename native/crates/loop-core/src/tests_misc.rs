use crate::*;

fn digest(seed: u8) -> String {
    hex(&[seed; 32])
}

fn draft(path: &str, seed: u8) -> ArtifactDraft {
    ArtifactDraft {
        schema_version: SCHEMA_VERSION,
        files: vec![FileEntry {
            path: path.into(),
            bytes: 10,
            digest: digest(seed),
        }],
    }
}

#[test]
fn settings_fail_closed() {
    assert!(Settings::default().validate().is_ok());
    let mut s = Settings::default();
    s.max_iterations = 0;
    assert_eq!(s.validate(), Err(LoopError::Settings));
    let mut s = Settings::default();
    s.required_checks.clear();
    assert_eq!(s.validate(), Err(LoopError::Settings));
    let mut s = Settings::default();
    s.protected_prefixes = vec!["../x/".into()];
    assert_eq!(s.validate(), Err(LoopError::Settings));
    let mut s = Settings::default();
    s.autonomous_repos = vec!["no-slash".into()];
    assert_eq!(s.validate(), Err(LoopError::Settings));
    assert!(Settings::from_json("{\"bogus\":1}").is_err());
    let text = serde_json::to_string(&Settings::default()).expect("json");
    assert_eq!(Settings::from_json(&text).expect("rt"), Settings::default());
}

#[test]
fn payload_parsing_denies_unknown_fields_and_oversize() {
    let ok = serde_json::to_string(&draft("a.rs", 1)).expect("json");
    assert!(parse::<ArtifactDraft>(&ok).is_ok());
    let extra = ok.replacen('{', "{\"extra\":1,", 1);
    assert_eq!(parse::<ArtifactDraft>(&extra).err(), Some(LoopError::Parse));
    assert_eq!(
        parse::<ArtifactDraft>(&"x".repeat(MAX_PAYLOAD + 1)).err(),
        Some(LoopError::TooLarge)
    );
}

#[test]
fn error_codes_roundtrip() {
    for code in [
        "loop.parse",
        "loop.protected",
        "loop.critic",
        "loop.serialize",
    ] {
        assert_eq!(LoopError::from_code(code).expect("code").code(), code);
    }
}
