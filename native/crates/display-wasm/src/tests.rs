use std::collections::BTreeMap;

use nuxiva_gesture_core::{
    Direction, Frame, GestureEvent, GestureKind, Hand, Handedness, LANDMARKS, Point, PointerPhase,
};

use crate::gate::{Audience, public_only, trusted};
use crate::hands::{HandsEngine, HandsError};
use crate::owner::{Face, Owner, assign};

fn hand(x: f32, y: f32) -> Hand {
    let points: Vec<Point> = (0..LANDMARKS)
        .map(|i| {
            let step = f32::from(u8::try_from(i).unwrap_or(0)) * 0.004;
            Point {
                x: x + step,
                y: y - step,
                z: 0.0,
            }
        })
        .collect();
    match Hand::new(&points, Handedness::Right, 0.9) {
        Ok(h) => h,
        Err(e) => unreachable!("{e}"),
    }
}

fn face(x: f32, y: f32, authorized: bool) -> Face {
    Face {
        x,
        y,
        w: 0.1,
        authorized,
    }
}

fn engine() -> HandsEngine {
    match HandsEngine::new("{}") {
        Ok(e) => e,
        Err(e) => unreachable!("{e}"),
    }
}

fn pointer_count(events: &[GestureEvent]) -> usize {
    events
        .iter()
        .filter(|e| matches!(e, GestureEvent::Pointer { .. }))
        .count()
}

fn run(engine: &mut HandsEngine, x: f32, y: f32) -> Vec<GestureEvent> {
    let mut out = Vec::new();
    for t in 0..30_u64 {
        let frame = Frame {
            timestamp_ms: t.saturating_mul(40),
            hands: vec![hand(x, y)],
        };
        out.extend(engine.feed(&frame, "desktop"));
    }
    out
}

#[test]
fn hands_belong_to_the_nearest_face_above_them() {
    let faces = [face(0.3, 0.3, true), face(0.7, 0.3, false)];
    assert_eq!(
        assign(&[hand(0.32, 0.6), hand(0.68, 0.6), hand(0.3, 0.02)], &faces),
        vec![Owner::Authorized, Owner::Guest, Owner::Unknown]
    );
    assert_eq!(
        assign(
            &[hand(0.32, 0.6)],
            &[Face {
                x: 2.0,
                y: 0.3,
                w: 0.1,
                authorized: true
            }]
        ),
        vec![Owner::Unknown]
    );
}

#[test]
fn only_trusted_owners_get_full_control() {
    use Audience::{Authorized, Empty, GuestOnly, Mixed, Uncertain};
    assert!(trusted(Owner::Authorized, Mixed, false));
    assert!(trusted(Owner::Unknown, Authorized, false));
    assert!(!trusted(Owner::Unknown, Mixed, false));
    assert!(trusted(Owner::Unknown, Mixed, true));
    assert!(!trusted(Owner::Guest, Mixed, false));
    assert!(!trusted(Owner::Guest, GuestOnly, true));
    assert!(!trusted(Owner::Unknown, Uncertain, true));
    assert!(!trusted(Owner::Authorized, Empty, true));
}

#[test]
fn guests_keep_only_public_actions() {
    let action = |name: &str, confirm: bool| GestureEvent::Action {
        action: name.to_owned(),
        args: BTreeMap::new(),
        gesture: GestureKind::Swipe(Direction::Left),
        hand: Handedness::Right,
        confirm,
    };
    let events = vec![
        action("volume.up", false),
        action("volume.up", true),
        action("scene.run", false),
        GestureEvent::Pointer {
            phase: PointerPhase::Move,
            x: 0.5,
            y: 0.5,
            pinch: false,
            flick: None,
        },
    ];
    let kept = public_only(events);
    assert_eq!(kept.len(), 1);
    assert!(matches!(&kept[..], [GestureEvent::Action { action, .. }] if action == "volume.up"));
}

#[test]
fn an_unknown_hand_cannot_drive_the_pointer_with_guests() {
    let mut e = engine();
    assert!(e.set_scene("[]", "guest_only", false).is_ok());
    assert_eq!(pointer_count(&run(&mut e, 0.5, 0.6)), 0);
    assert_eq!(e.tally().trusted, 0);
    let mut owner = engine();
    assert!(owner.set_scene("[]", "authorized", false).is_ok());
    assert!(pointer_count(&run(&mut owner, 0.5, 0.6)) > 0);
}

#[test]
fn an_authorized_face_unlocks_its_own_hand_in_a_mixed_room() {
    let mut e = engine();
    assert!(
        e.set_scene(
            r#"[{"x":0.5,"y":0.3,"w":0.1,"authorized":true}]"#,
            "mixed",
            false
        )
        .is_ok()
    );
    assert!(pointer_count(&run(&mut e, 0.5, 0.6)) > 0);
    let mut g = engine();
    assert!(
        g.set_scene(
            r#"[{"x":0.5,"y":0.3,"w":0.1,"authorized":false}]"#,
            "mixed",
            false
        )
        .is_ok()
    );
    assert_eq!(pointer_count(&run(&mut g, 0.5, 0.6)), 0);
}

#[test]
fn bad_scenes_and_frames_are_rejected() {
    let mut e = engine();
    assert_eq!(
        e.set_scene(r#"[{"x":3,"y":0.3,"w":0.1}]"#, "mixed", false),
        Err(HandsError::Faces)
    );
    assert_eq!(e.set_scene("nope", "mixed", false), Err(HandsError::Faces));
    let many = format!("[{}]", vec![r#"{"x":0.5,"y":0.5,"w":0.1}"#; 17].join(","));
    assert_eq!(e.set_scene(&many, "mixed", false), Err(HandsError::Faces));
    assert!(
        e.feed_json(
            "{\"t\":1,\"hands\":[{\"handedness\":\"right\",\"score\":1,\"points\":[[0,0,0]]}]}",
            "desktop"
        )
        .is_err()
    );
    assert!(HandsEngine::new("not json").is_err());
}
