use nuxiva_context_core::{ContextSettings, Delta, Lang, Sealer, SharedContext};

use crate::tests::{fuse, fuser, household, ident, presence, speaker};
use crate::{Fusion, Observation};

#[test]
fn a_clock_set_back_keeps_a_fresh_observation_and_a_clock_set_far_ahead_expires_it() {
    let mut f = fuser();
    f.observe(speaker("anna", 950, 10_000), 9_000).expect("obs");
    assert_eq!(fuse(&f, 9_000).speaker, Some(ident("anna")));
    assert!(fuse(&f, 10_000 + 86_400_000).speaker.is_none());
}

#[test]
fn an_observation_from_the_far_future_is_refused() {
    let mut f = fuser();
    assert!(
        f.observe(speaker("anna", 950, 1_000_000_000), 1_000)
            .is_err()
    );
    assert!(f.observe(presence(&["ospite"], u64::MAX), 1_000).is_err());
    assert!(fuse(&f, 1_000).speaker.is_none());
}

#[test]
fn a_flood_of_observations_keeps_a_bounded_state_and_a_valid_percept() {
    let mut f = fuser();
    for at in 0..50_000_u64 {
        let person = if at % 2 == 0 { "anna" } else { "luca" };
        f.observe(speaker(person, 900, at), at).expect("obs");
        f.observe(presence(&[person], at), at).expect("obs");
    }
    let percept = fuse(&f, 50_000);
    assert_eq!(percept.speaker, Some(ident("luca")));
    assert!(percept.presence.len() <= 2);
}

#[test]
fn a_missing_or_empty_memory_source_degrades_to_an_empty_view_without_failing() {
    let empty =
        SharedContext::new(ContextSettings::default(), Sealer::from_key([1; 32])).expect("ctx");
    let fusion = Fusion::new(empty);
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    let view = fusion.view(&fuse(&f, 2_000), Lang::It, 0).expect("view");
    assert!(view.is_empty());
}

#[test]
fn a_person_removed_while_speaking_does_not_break_the_next_turn() {
    let ctx = household();
    let fusion = Fusion::new(ctx.clone());
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(
        Observation::Emotion {
            person: ident("anna"),
            valence: 500,
            arousal: 500,
            source: ident("voce"),
            at_ms: 1_000,
        },
        1_000,
    )
    .expect("obs");
    ctx.apply(Delta::Remove(crate::tests::pid("anna")))
        .expect("remove");
    let view = fusion.view(&fuse(&f, 2_000), Lang::It, 0).expect("view");
    assert!(!view.contains("arachidi"));
}

#[test]
fn a_new_access_rule_in_the_settings_changes_who_sees_a_field_without_new_code() {
    let strict = household();
    let relaxed = SharedContext::new(
        ContextSettings::from_json(
            r#"{"policy":{"audience":{"identity":"anyone","music":"anyone"}}}"#,
        )
        .expect("settings"),
        Sealer::from_key([9; 32]),
    )
    .expect("ctx");
    let deltas = vec![Delta::Upsert(Box::new(crate::tests::person(
        &relaxed,
        "anna",
        nuxiva_context_core::Role::Family,
        "arachidi",
        "jazz",
    )))];
    relaxed.apply_all(deltas).expect("seed");
    let mut f = fuser();
    f.observe(speaker("anna", 950, 1_000), 1_000).expect("obs");
    f.observe(presence(&["ospite"], 1_000), 1_000).expect("obs");
    let percept = fuse(&f, 2_000);
    let hidden = Fusion::new(strict)
        .view(&percept, Lang::It, 0)
        .expect("view");
    let shown = Fusion::new(relaxed)
        .view(&percept, Lang::It, 0)
        .expect("view");
    assert!(!hidden.contains("jazz"));
    assert!(shown.contains("jazz"));
}
