use crate::policy::Policy;
use crate::signal::{Face, Liveness, Signals, Vision, Voice};
use crate::tracker::Tracker;
use nuxiva_display_domain::AudienceKind;

fn face(person: &str, liveness: Liveness) -> Face {
    Face {
        person: Some(person.into()),
        authorized: true,
        confidence: 0.9,
        liveness,
        near: true,
    }
}

fn webcam(liveness: Liveness, voice_at: Option<u64>) -> Signals {
    Signals {
        vision: Vision::Ok,
        faces: vec![face("nunzio", liveness)],
        voices: voice_at
            .map(|at_ms| Voice {
                person: Some("nunzio".into()),
                authorized: true,
                score: 0.8,
                at_ms,
            })
            .into_iter()
            .collect(),
    }
}

fn opened(tracker: &mut Tracker) {
    tracker.step(&webcam(Liveness::Unknown, Some(0)), 0);
    assert_eq!(
        tracker
            .step(&webcam(Liveness::Unknown, Some(0)), 1_500)
            .kind,
        AudienceKind::Authorized
    );
}

#[test]
fn a_spoken_owner_stays_authorized_while_the_face_stays_in_view() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    for now in (2_000..=29_000).step_by(1_000) {
        assert_eq!(
            tracker.step(&webcam(Liveness::Unknown, None), now).kind,
            AudienceKind::Authorized,
            "at {now}"
        );
    }
}

#[test]
fn the_hold_ends_with_the_configured_voice_time() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    for now in (2_000..=35_000).step_by(1_000) {
        assert_eq!(
            tracker.step(&webcam(Liveness::Unknown, None), now).kind,
            AudienceKind::Authorized,
            "at {now}"
        );
    }
    assert_eq!(
        tracker.step(&webcam(Liveness::Unknown, None), 36_000).kind,
        AudienceKind::Uncertain
    );
}

#[test]
fn speaking_again_renews_the_hold() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    for now in (2_000..=50_000).step_by(1_000) {
        let voice = (now == 25_000).then_some(25_000);
        assert_eq!(
            tracker.step(&webcam(Liveness::Unknown, voice), now).kind,
            AudienceKind::Authorized,
            "at {now}"
        );
    }
}

#[test]
fn losing_the_face_breaks_the_hold() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    let mut empty = webcam(Liveness::Unknown, None);
    empty.faces.clear();
    tracker.step(&empty, 2_000);
    tracker.step(&empty, 6_000);
    tracker.step(&webcam(Liveness::Unknown, None), 12_000);
    assert_eq!(
        tracker.step(&webcam(Liveness::Unknown, None), 18_000).kind,
        AudienceKind::Uncertain
    );
}

#[test]
fn a_spoof_cancels_the_hold() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    tracker.step(&webcam(Liveness::Spoof, None), 2_000);
    assert_eq!(
        tracker.step(&webcam(Liveness::Unknown, None), 2_500).kind,
        AudienceKind::Uncertain
    );
}

#[test]
fn a_camera_fault_cancels_the_hold() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    let mut fault = webcam(Liveness::Unknown, None);
    fault.vision = Vision::Offline;
    tracker.step(&fault, 2_000);
    assert_eq!(
        tracker.step(&webcam(Liveness::Unknown, None), 2_500).kind,
        AudienceKind::Uncertain
    );
}

#[test]
fn a_photo_never_spoken_for_opens_nothing() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    for now in (0..=20_000).step_by(1_000) {
        assert_ne!(
            tracker.step(&webcam(Liveness::Unknown, None), now).kind,
            AudienceKind::Authorized
        );
    }
}

#[test]
fn a_zero_voice_time_disables_the_hold() {
    let policy = Policy {
        voice_hold_ms: 0,
        ..Policy::default()
    };
    let mut tracker = Tracker::new(policy, 0);
    opened(&mut tracker);
    tracker.step(&webcam(Liveness::Unknown, None), 11_000);
    assert_eq!(
        tracker.step(&webcam(Liveness::Unknown, None), 17_000).kind,
        AudienceKind::Uncertain
    );
}
