use crate::tests::{cand, catalog, refl, store};
use crate::*;

#[test]
fn export_import_roundtrip_and_hostile_snapshots() {
    let mut s = store();
    let id = s
        .record(
            &refl(
                "a",
                Outcome::Success,
                1,
                &[("tone", "warm")],
                cand("tone", "warm"),
            ),
            0,
        )
        .expect("a")
        .candidate
        .expect("id");
    s.confirm(id, 1).expect("confirm");
    let text = s.export().expect("export");
    let back = Store::import(Settings::default(), catalog(), &text).expect("import");
    assert_eq!(back.lesson_for("tone").expect("tone").value, "warm");
    assert_eq!(back.history_len(), 1);
    let tampered = text.replace("\"warm\"", "\"hot\u{0}\"");
    assert!(Store::import(Settings::default(), catalog(), &tampered).is_err());
    let unknown = text.replace("\"tone\"", "\"ghost\"");
    assert_eq!(
        Store::import(Settings::default(), catalog(), &unknown).err(),
        Some(ReflectError::Invalid)
    );
    assert_eq!(
        Store::import(Settings::default(), catalog(), &"x".repeat(MAX_PAYLOAD + 1)).err(),
        Some(ReflectError::TooLarge)
    );
    assert_eq!(
        Store::import(Settings::default(), catalog(), "nope").err(),
        Some(ReflectError::Parse)
    );
    assert_eq!(
        Store::import(
            Settings::default(),
            catalog(),
            &text.replace(
                "\"schema_version\":1,\"next_id\"",
                "\"schema_version\":4,\"next_id\""
            )
        )
        .err(),
        Some(ReflectError::Version)
    );
}

#[test]
fn settings_and_catalog_fail_closed() {
    assert!(Settings::default().validate().is_ok());
    let mut s = Settings::default();
    s.min_samples = 0;
    assert_eq!(s.validate(), Err(ReflectError::Settings));
    assert!(Settings::from_json("{\"x\":1}").is_err());
    assert_eq!(
        Catalog::from_json("{\"kinds\":{}}").err(),
        Some(ReflectError::Catalog)
    );
    assert!(
        Catalog::from_json("{\"kinds\":{\"Bad Name\":{\"domain\":\"a\",\"max_value_len\":4}}}")
            .is_err()
    );
    let text = serde_json::to_string(&Settings::default()).expect("json");
    assert_eq!(Settings::from_json(&text).expect("rt"), Settings::default());
}

#[test]
fn randomized_runs_never_keep_a_harmful_unconfirmed_lesson_and_stay_reversible() {
    let mut state = 0x9e37_79b9_7f4a_7c15u64;
    let mut next = move || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let mut s = store();
    for step in 0..3_000u64 {
        let value = if next() % 2 == 0 {
            "morning"
        } else {
            "evening"
        };
        let outcome = if next() % 3 == 0 {
            Outcome::Failure
        } else {
            Outcome::Success
        };
        let proposed = if next() % 5 == 0 {
            cand("reminder_time", value)
        } else {
            None
        };
        s.record(
            &refl(
                &format!("t{step}"),
                outcome,
                1 + (next() % 3) as u32,
                &[("reminder_time", value)],
                proposed,
            ),
            step,
        )
        .expect("record");
        for lesson in s.lessons(LessonState::Adopted) {
            if !lesson.user_confirmed {
                let v = s.verify(lesson);
                assert!(
                    !(v.treated >= 5 && v.treated_mean < v.baseline_mean),
                    "step {step}: {v:?}"
                );
            }
        }
    }
    while s.revert("reminder_time", 9_999).is_ok() {}
    assert!(s.lesson_for("reminder_time").is_none());
}

#[test]
fn no_code_path_applies_a_code_delta() {
    let src = std::fs::read_to_string(
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/store.rs"),
    )
    .expect("src");
    assert!(!src.contains("fn apply"));
    assert!(!src.contains("std::process"));
    assert!(!src.contains("std::fs"));
}

#[test]
fn error_codes_roundtrip() {
    for code in ["reflect.parse", "reflect.blocked", "reflect.serialize"] {
        assert_eq!(ReflectError::from_code(code).expect("code").code(), code);
    }
}
