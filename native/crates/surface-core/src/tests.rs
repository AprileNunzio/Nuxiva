use crate::descriptor::{RoomPose, SurfaceDescriptor};
use crate::layout::Screen;
use crate::{Audience, Direction, Layout, MoveGuard, MoveOrigin, RoomAudience};

fn placed(n: u8, room: &str, x_m: f32, y_m: f32, z_m: f32, yaw_deg: f32) -> Screen {
    Screen {
        n,
        x: 0,
        surface: SurfaceDescriptor {
            placement: Some(RoomPose {
                room: room.to_owned(),
                x_m,
                y_m,
                z_m,
                yaw_deg,
            }),
            ..SurfaceDescriptor::default()
        },
    }
}

fn flat(n: u8, x: i32) -> Screen {
    Screen {
        n,
        x,
        surface: SurfaceDescriptor::default(),
    }
}

#[test]
fn ordered_fallback_follows_x() {
    let layout = Layout::new(vec![flat(2, 200), flat(0, 0), flat(1, 100)]);
    assert_eq!(layout.numbers(), vec![0, 1, 2]);
    assert_eq!(layout.neighbor(1, Direction::Left), Some(0));
    assert_eq!(layout.neighbor(1, Direction::Right), Some(2));
    assert_eq!(layout.neighbor(0, Direction::Left), None);
    assert_eq!(layout.neighbor(1, Direction::Up), None);
}

#[test]
fn physical_neighbors_use_pose() {
    let layout = Layout::new(vec![
        placed(0, "living", 0.0, 0.0, 1.0, 0.0),
        placed(1, "living", 1.5, 0.0, 1.0, 0.0),
        placed(2, "living", 4.0, 0.2, 1.0, 0.0),
        placed(3, "living", 0.1, 0.0, 2.2, 0.0),
        placed(4, "kitchen", -1.0, 0.0, 1.0, 0.0),
    ]);
    let around = layout.neighbors(0);
    assert_eq!(around.right, Some(1));
    assert_eq!(around.up, Some(3));
    assert_eq!(around.left, None);
    assert_eq!(around.down, None);
    assert_eq!(layout.neighbor(1, Direction::Right), Some(2));
    assert_eq!(layout.room_of(4), Some("kitchen"));
}

#[test]
fn yaw_rotates_sides() {
    let layout = Layout::new(vec![
        placed(0, "hall", 0.0, 0.0, 1.0, 90.0),
        placed(1, "hall", 0.0, -2.0, 1.0, 0.0),
    ]);
    assert_eq!(layout.neighbor(0, Direction::Right), Some(1));
    assert_eq!(layout.neighbor(0, Direction::Left), None);
}

#[test]
fn insane_descriptors_are_dropped() {
    let mut bad = flat(1, 10);
    bad.surface.width = 0;
    let mut room = placed(2, "Living Room", 0.0, 0.0, 0.0, 0.0);
    room.x = 20;
    let layout = Layout::new(vec![flat(0, 0), bad, room, flat(40, 30)]);
    assert_eq!(layout.numbers(), vec![0]);
}

#[test]
fn planner_moves_are_held() {
    let mut guard = MoveGuard::new(30_000);
    assert_eq!(guard.decide("clock", 0, MoveOrigin::Planner, 0, &[0, 1]), 0);
    assert_eq!(
        guard.decide("clock", 1, MoveOrigin::Planner, 10_000, &[0, 1]),
        0
    );
    assert_eq!(
        guard.decide("clock", 1, MoveOrigin::Planner, 30_001, &[0, 1]),
        1
    );
    assert_eq!(
        guard.decide("clock", 0, MoveOrigin::User, 30_002, &[0, 1]),
        0
    );
}

#[test]
fn dead_screens_release_hold() {
    let mut guard = MoveGuard::new(30_000);
    guard.decide("news", 1, MoveOrigin::Planner, 0, &[0, 1]);
    assert_eq!(guard.decide("news", 0, MoveOrigin::Planner, 5, &[0]), 0);
    guard.forget(&[]);
    assert_eq!(guard.decide("news", 1, MoveOrigin::Planner, 6, &[0, 1]), 1);
}

#[test]
fn room_audience_strictness() {
    let mut audience = RoomAudience {
        global: Audience::Authorized,
        rooms: [("kitchen".to_owned(), Audience::GuestOnly)]
            .into_iter()
            .collect(),
        sensed: vec!["living".to_owned()],
        strict: false,
    };
    assert_eq!(audience.for_room(Some("kitchen")), Audience::GuestOnly);
    assert_eq!(audience.for_room(Some("living")), Audience::Authorized);
    assert_eq!(audience.for_room(Some("garage")), Audience::Authorized);
    assert_eq!(audience.for_room(None), Audience::Authorized);
    audience.strict = true;
    assert_eq!(audience.for_room(Some("garage")), Audience::Uncertain);
}

#[test]
fn descriptor_round_trips() {
    let raw = r#"{"kind":"xr_headset","width":3664,"height":1920,"refresh_hz":90,"stereo":true,"views":2,"input":{"hands":true,"gaze":true}}"#;
    let parsed: Result<SurfaceDescriptor, _> = serde_json::from_str(raw);
    assert!(parsed.as_ref().is_ok_and(SurfaceDescriptor::sane));
    let rejected: Result<SurfaceDescriptor, _> = serde_json::from_str(r#"{"bogus":1}"#);
    assert!(rejected.is_err());
}
