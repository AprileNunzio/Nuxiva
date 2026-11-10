use crate::fusion::{Proof, fuse};
use crate::policy::Policy;
use crate::signal::{Face, Liveness, Signals, Vision, Voice};
use crate::tracker::Tracker;
use nuxiva_display_domain::AudienceKind;

fn owner(liveness: Liveness) -> Face {
    Face {
        person: Some("nunzio".into()),
        authorized: true,
        confidence: 0.9,
        liveness,
        near: true,
    }
}

fn stranger() -> Face {
    Face {
        person: None,
        authorized: false,
        confidence: 0.9,
        liveness: Liveness::Live,
        near: true,
    }
}

fn staff() -> Face {
    Face {
        person: Some("maria".into()),
        authorized: false,
        confidence: 0.9,
        liveness: Liveness::Live,
        near: false,
    }
}

fn voice(at_ms: u64) -> Voice {
    Voice {
        person: Some("nunzio".into()),
        authorized: true,
        score: 0.8,
        at_ms,
    }
}

fn seen(faces: Vec<Face>) -> Signals {
    Signals {
        vision: Vision::Ok,
        faces,
        voices: Vec::new(),
    }
}

fn kind(signals: &Signals) -> AudienceKind {
    fuse(signals, &Policy::default(), 10_000).kind
}

#[test]
fn nobody_in_view_is_empty() {
    assert_eq!(kind(&seen(Vec::new())), AudienceKind::Empty);
}

#[test]
fn a_live_owner_is_authorized() {
    assert_eq!(
        kind(&seen(vec![owner(Liveness::Live)])),
        AudienceKind::Authorized
    );
}

#[test]
fn strangers_and_unauthorized_people_are_guests() {
    assert_eq!(kind(&seen(vec![stranger()])), AudienceKind::GuestOnly);
    assert_eq!(kind(&seen(vec![staff()])), AudienceKind::GuestOnly);
}

#[test]
fn owner_with_a_guest_is_mixed() {
    assert_eq!(
        kind(&seen(vec![owner(Liveness::Live), stranger()])),
        AudienceKind::Mixed
    );
}

#[test]
fn a_photo_of_the_owner_opens_nothing() {
    assert_eq!(
        kind(&seen(vec![owner(Liveness::Spoof)])),
        AudienceKind::GuestOnly
    );
    assert_eq!(
        kind(&seen(vec![owner(Liveness::Unknown)])),
        AudienceKind::Uncertain
    );
}

#[test]
fn unknown_liveness_is_accepted_only_when_the_owner_turned_it_off() {
    let policy = Policy {
        require_liveness: false,
        ..Policy::default()
    };
    assert_eq!(
        fuse(&seen(vec![owner(Liveness::Unknown)]), &policy, 0).kind,
        AudienceKind::Authorized
    );
}

#[test]
fn a_matching_voice_corroborates_an_unverified_face() {
    let mut signals = seen(vec![owner(Liveness::Unknown)]);
    signals.voices.push(voice(9_000));
    assert_eq!(kind(&signals), AudienceKind::Authorized);
}

#[test]
fn face_and_voice_together_are_strong() {
    let mut signals = seen(vec![owner(Liveness::Live)]);
    signals.voices.push(voice(9_500));
    let reading = fuse(&signals, &Policy::default(), 10_000);
    assert_eq!(
        reading.members.first().map(|m| m.proof),
        Some(Proof::Strong)
    );
}

#[test]
fn low_confidence_and_nan_faces_are_unverified() {
    let mut weak = owner(Liveness::Live);
    weak.confidence = 0.2;
    assert_eq!(kind(&seen(vec![weak.clone()])), AudienceKind::Uncertain);
    weak.confidence = f32::NAN;
    assert_eq!(kind(&seen(vec![weak])), AudienceKind::Uncertain);
}

#[test]
fn stale_or_future_voices_are_ignored() {
    let mut signals = seen(Vec::new());
    signals.voices.push(voice(0));
    signals.voices.push(voice(60_000));
    assert_eq!(kind(&signals), AudienceKind::Empty);
}

#[test]
fn a_broken_camera_fails_closed_and_a_disabled_one_is_unmonitored() {
    let mut signals = seen(vec![owner(Liveness::Live)]);
    signals.vision = Vision::Offline;
    assert_eq!(kind(&signals), AudienceKind::Uncertain);
    signals.vision = Vision::Disabled;
    assert_eq!(kind(&signals), AudienceKind::Authorized);
}

#[test]
fn opening_waits_for_stability() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let owner_only = seen(vec![owner(Liveness::Live)]);
    assert_eq!(tracker.step(&seen(Vec::new()), 0).kind, AudienceKind::Empty);
    assert_eq!(tracker.step(&owner_only, 100).kind, AudienceKind::Empty);
    assert_eq!(tracker.step(&owner_only, 800).kind, AudienceKind::Empty);
    assert_eq!(
        tracker.step(&owner_only, 1_300).kind,
        AudienceKind::Authorized
    );
}

#[test]
fn a_guest_closes_immediately() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let owner_only = seen(vec![owner(Liveness::Live)]);
    tracker.step(&owner_only, 0);
    tracker.step(&owner_only, 1_500);
    let audience = tracker.step(&seen(vec![owner(Liveness::Live), stranger()]), 1_510);
    assert_eq!(audience.kind, AudienceKind::Mixed);
    assert_eq!(audience.since_ms, 1_510);
}

#[test]
fn leaving_waits_for_the_away_time() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let owner_only = seen(vec![owner(Liveness::Live)]);
    tracker.step(&owner_only, 0);
    tracker.step(&owner_only, 1_500);
    assert_eq!(
        tracker.step(&seen(Vec::new()), 5_000).kind,
        AudienceKind::Authorized
    );
    let gone = tracker.step(&seen(Vec::new()), 11_600);
    assert_eq!(gone.kind, AudienceKind::Empty);
    assert!(gone.nucleus_only);
}

#[test]
fn an_authorized_voice_holds_the_scene_when_the_face_is_lost() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let mut talking = seen(vec![owner(Liveness::Live)]);
    tracker.step(&talking, 0);
    tracker.step(&talking, 1_500);
    talking.faces.clear();
    talking.voices.push(voice(2_000));
    assert_eq!(tracker.step(&talking, 2_000).kind, AudienceKind::Authorized);
    let silent = seen(Vec::new());
    assert_eq!(tracker.step(&silent, 25_000).kind, AudienceKind::Authorized);
    assert_eq!(tracker.step(&silent, 33_000).kind, AudienceKind::Empty);
}

#[test]
fn a_camera_fault_closes_the_scene_at_once() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let owner_only = seen(vec![owner(Liveness::Live)]);
    tracker.step(&owner_only, 0);
    tracker.step(&owner_only, 1_500);
    let fault = Signals {
        vision: Vision::Offline,
        ..Signals::default()
    };
    assert_eq!(tracker.step(&fault, 1_600).kind, AudienceKind::Uncertain);
}

#[test]
fn the_guest_leaving_needs_stability_to_reopen() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let mixed = seen(vec![owner(Liveness::Live), stranger()]);
    let owner_only = seen(vec![owner(Liveness::Live)]);
    tracker.step(&mixed, 0);
    tracker.step(&mixed, 1_500);
    assert_eq!(tracker.step(&owner_only, 2_000).kind, AudienceKind::Mixed);
    assert_eq!(
        tracker.step(&owner_only, 3_300).kind,
        AudienceKind::Authorized
    );
}

#[test]
fn flicker_restarts_the_stability_window() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let owner_only = seen(vec![owner(Liveness::Live)]);
    tracker.step(&seen(Vec::new()), 0);
    tracker.step(&owner_only, 100);
    tracker.step(&seen(vec![stranger()]), 600);
    assert_eq!(
        tracker.step(&owner_only, 1_400).kind,
        AudienceKind::GuestOnly
    );
    assert_eq!(
        tracker.step(&owner_only, 2_700).kind,
        AudienceKind::Authorized
    );
}

#[test]
fn signals_reject_unknown_fields() {
    let raw = r#"{"vision":"ok","faces":[{"person":"x","admin":true}]}"#;
    assert!(serde_json::from_str::<Signals>(raw).is_err());
}

#[test]
fn the_audience_never_reports_identities_for_guests() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let audience = tracker.step(&seen(vec![stranger(), staff()]), 0);
    assert_eq!(audience.members, [] as [crate::fusion::Member; 0]);
    assert_eq!(audience.guests, 2);
}
