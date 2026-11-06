use crate::policy::Policy;
use crate::signal::{Face, Liveness, Signals, Vision, Voice};
use crate::tracker::Tracker;
use nuxiva_display_domain::AudienceKind;

fn face(liveness: Liveness, confidence: f32) -> Face {
    Face {
        person: Some("nunzio".into()),
        authorized: true,
        confidence,
        liveness,
        near: true,
    }
}

fn stranger() -> Face {
    Face {
        person: None,
        authorized: false,
        confidence: 0.0,
        liveness: Liveness::Unknown,
        near: false,
    }
}

fn scene(faces: Vec<Face>, voice_at: Option<u64>) -> Signals {
    Signals {
        vision: Vision::Ok,
        faces,
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
    let talking = scene(vec![face(Liveness::Unknown, 0.9)], Some(0));
    tracker.step(&talking, 0);
    assert_eq!(tracker.step(&talking, 1_500).kind, AudienceKind::Authorized);
}

#[test]
fn a_brief_recognition_dip_keeps_the_widgets() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    let dip = scene(vec![face(Liveness::Unknown, 0.3)], None);
    for now in (12_000..=16_000).step_by(1_000) {
        assert_eq!(
            tracker.step(&dip, now).kind,
            AudienceKind::Authorized,
            "at {now}"
        );
    }
    let clear = scene(vec![face(Liveness::Unknown, 0.9)], None);
    assert_eq!(tracker.step(&clear, 17_000).kind, AudienceKind::Authorized);
}

#[test]
fn a_lasting_doubt_still_closes() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    let dip = scene(vec![face(Liveness::Unknown, 0.3)], None);
    tracker.step(&dip, 12_000);
    assert_eq!(tracker.step(&dip, 18_000).kind, AudienceKind::Uncertain);
}

#[test]
fn a_live_face_keeps_its_hold_after_liveness_fades() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let live = scene(vec![face(Liveness::Live, 0.9)], None);
    tracker.step(&live, 0);
    assert_eq!(tracker.step(&live, 1_500).kind, AudienceKind::Authorized);
    let faded = scene(vec![face(Liveness::Unknown, 0.9)], None);
    for now in (2_000..=30_000).step_by(1_000) {
        assert_eq!(
            tracker.step(&faded, now).kind,
            AudienceKind::Authorized,
            "at {now}"
        );
    }
}

#[test]
fn the_speaker_own_weak_face_is_not_a_stranger() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    let talking = scene(vec![face(Liveness::Unknown, 0.3)], Some(0));
    tracker.step(&talking, 0);
    assert_eq!(tracker.step(&talking, 1_500).kind, AudienceKind::Authorized);
}

#[test]
fn a_stranger_still_closes_at_once() {
    let mut tracker = Tracker::new(Policy::default(), 0);
    opened(&mut tracker);
    let intruder = scene(vec![stranger()], None);
    assert_eq!(tracker.step(&intruder, 2_000).kind, AudienceKind::GuestOnly);
}
