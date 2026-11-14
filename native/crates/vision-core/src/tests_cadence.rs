use crate::buffer::Source;
use crate::cadence::{Cadence, THUMB_H, THUMB_W, Verdict, dhash};

fn gradient(flip: bool) -> Vec<u8> {
    (0..THUMB_W * THUMB_H)
        .map(|i| {
            let col = u8::try_from(i % THUMB_W).unwrap_or(0);
            if flip {
                col.saturating_mul(20)
            } else {
                200_u8.saturating_sub(col.saturating_mul(20))
            }
        })
        .collect()
}

#[test]
fn dhash_rejects_wrong_size() {
    assert!(dhash(&[0; 10]).is_none());
    assert!(dhash(&gradient(true)).is_some());
}

#[test]
fn dhash_separates_opposite_gradients() {
    let a = dhash(&gradient(true)).unwrap_or(0);
    let b = dhash(&gradient(false)).unwrap_or(0);
    assert!((a ^ b).count_ones() > 32);
    assert_eq!(a, dhash(&gradient(true)).unwrap_or(1));
}

#[test]
fn first_frame_embeds_then_not_due() {
    let mut c = Cadence::new(1_000, 8_000);
    assert_eq!(c.admit(Source::Screen, 7, 0), Verdict::Embed);
    assert_eq!(c.admit(Source::Screen, 9, 500), Verdict::NotDue);
}

#[test]
fn identical_frames_back_off_until_ceiling() {
    let mut c = Cadence::new(1_000, 4_000);
    let mut now = 0;
    assert_eq!(c.admit(Source::Screen, 5, now), Verdict::Embed);
    for _ in 0..12 {
        now += c.interval_ms(Source::Screen);
        assert_eq!(c.admit(Source::Screen, 5, now), Verdict::Unchanged);
    }
    assert_eq!(c.interval_ms(Source::Screen), 4_000);
    assert!(c.unchanged_streak(Source::Screen) >= 12);
}

#[test]
fn change_resets_interval() {
    let mut c = Cadence::new(1_000, 8_000);
    let mut now = 0;
    c.admit(Source::Webcam, 0, now);
    for _ in 0..3 {
        now += c.interval_ms(Source::Webcam);
        c.admit(Source::Webcam, 0, now);
    }
    assert!(c.interval_ms(Source::Webcam) > 1_000);
    now += c.interval_ms(Source::Webcam);
    assert_eq!(c.admit(Source::Webcam, u64::MAX, now), Verdict::Embed);
    assert_eq!(c.interval_ms(Source::Webcam), 1_000);
}

#[test]
fn lanes_are_independent() {
    let mut c = Cadence::new(1_000, 8_000);
    assert_eq!(c.admit(Source::Screen, 1, 0), Verdict::Embed);
    assert!(c.due(Source::Webcam, 0));
    assert_eq!(c.admit(Source::Webcam, 1, 0), Verdict::Embed);
}

#[test]
fn bounds_are_clamped() {
    let c = Cadence::new(1, u64::MAX);
    assert_eq!(c.interval_ms(Source::Screen), 250);
}

#[test]
fn screens_blocks_without_consent_and_for_sensitive_windows() {
    use crate::{Policy, VisualBuffer};
    let mut buffer = VisualBuffer::new(Policy::new(false, 1_000, 60_000, 8));
    assert!(buffer.screens("editor", "notes"));
    buffer.set_policy(Policy::new(true, 1_000, 60_000, 8));
    assert!(!buffer.screens("editor", "notes"));
    assert!(buffer.screens("1Password", "vault"));
    assert!(buffer.screens("firefox", "Home banking - login"));
}

#[test]
fn throttle_is_per_source() {
    use crate::{FrameMeta, Policy, PushOutcome, VisualBuffer};
    let mut buffer = VisualBuffer::new(Policy::new(true, 1_000, 60_000, 8));
    let screen = FrameMeta {
        source: Source::Screen,
        app: "a".into(),
        title: String::new(),
        at_ms: 5_000,
    };
    let webcam = FrameMeta {
        source: Source::Webcam,
        app: "webcam".into(),
        title: String::new(),
        at_ms: 5_000,
    };
    let vector = [1.0_f32, 0.5, 0.25];
    assert_eq!(buffer.push(&screen, &vector), PushOutcome::Stored);
    assert_eq!(buffer.push(&webcam, &vector), PushOutcome::Stored);
    let again = FrameMeta {
        at_ms: 5_100,
        ..screen
    };
    assert!(matches!(
        buffer.push(&again, &vector),
        PushOutcome::Rejected(_)
    ));
}
