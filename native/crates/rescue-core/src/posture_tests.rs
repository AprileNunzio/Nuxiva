use crate::posture::{Body, Posture, PostureConfig, PostureKind};

const FW: f64 = 1280.0;
const FH: f64 = 720.0;

fn standing(x: f64) -> Body {
    Body {
        x,
        y: 120.0,
        w: 160.0,
        h: 480.0,
        score: 0.9,
        rest: false,
    }
}

fn lying(x: f64, rest: bool) -> Body {
    Body {
        x,
        y: 480.0,
        w: 460.0,
        h: 150.0,
        score: 0.85,
        rest,
    }
}

fn sitting(x: f64) -> Body {
    Body {
        x,
        y: 300.0,
        w: 220.0,
        h: 260.0,
        score: 0.88,
        rest: false,
    }
}

fn engine() -> Posture {
    let made = Posture::new(PostureConfig::default());
    assert!(made.is_some());
    made.unwrap_or_else(|| unreachable!())
}

fn run(p: &mut Posture, frames: &[(f64, Vec<Body>)]) -> Vec<PostureKind> {
    frames
        .iter()
        .flat_map(|(t, b)| p.observe("cam.main", *t, FW, FH, b))
        .map(|e| e.kind)
        .collect()
}

fn timeline(start: f64, end: f64, every: f64, body: Body) -> Vec<(f64, Vec<Body>)> {
    let mut out = Vec::new();
    let mut t = start;
    while t <= end {
        out.push((t, vec![body]));
        t += every;
    }
    out
}

#[test]
fn sudden_fall_then_lying_is_a_fall_and_later_immobility() {
    let mut p = engine();
    let mut frames = timeline(0.0, 5.0, 1.2, standing(500.0));
    frames.extend(timeline(6.0, 80.0, 1.2, lying(420.0, false)));
    let kinds = run(&mut p, &frames);
    assert_eq!(kinds.iter().filter(|k| **k == PostureKind::Fall).count(), 1);
    assert_eq!(
        kinds
            .iter()
            .filter(|k| **k == PostureKind::Immobility)
            .count(),
        1
    );
}

#[test]
fn quick_bend_is_not_a_fall() {
    let mut p = engine();
    let mut frames = timeline(0.0, 5.0, 1.2, standing(500.0));
    frames.extend(timeline(6.0, 8.0, 1.0, lying(420.0, false)));
    frames.extend(timeline(9.0, 20.0, 1.2, standing(500.0)));
    assert!(!run(&mut p, &frames).contains(&PostureKind::Fall));
}

#[test]
fn slowly_lying_down_through_sitting_is_not_a_fall() {
    let mut p = engine();
    let mut frames = timeline(0.0, 5.0, 1.2, standing(500.0));
    frames.extend(timeline(6.0, 12.0, 1.2, sitting(480.0)));
    frames.extend(timeline(13.0, 40.0, 1.2, lying(420.0, false)));
    assert!(!run(&mut p, &frames).contains(&PostureKind::Fall));
}

#[test]
fn resting_on_a_bed_is_never_immobility() {
    let mut p = engine();
    let mut frames = timeline(0.0, 3.0, 1.2, standing(500.0));
    frames.extend(timeline(10.0, 400.0, 1.2, lying(420.0, true)));
    assert!(
        run(&mut p, &frames)
            .iter()
            .all(|k| *k != PostureKind::Immobility)
    );
}

#[test]
fn falling_onto_a_sofa_counts_less() {
    let mut a = engine();
    let mut b = engine();
    let mut floor = timeline(0.0, 5.0, 1.2, standing(500.0));
    let mut sofa = floor.clone();
    floor.extend(timeline(6.0, 15.0, 1.2, lying(420.0, false)));
    sofa.extend(timeline(6.0, 15.0, 1.2, lying(420.0, true)));
    let pa = floor
        .iter()
        .flat_map(|(t, bd)| a.observe("c", *t, FW, FH, bd))
        .map(|e| e.probability)
        .fold(0.0, f64::max);
    let pb = sofa
        .iter()
        .flat_map(|(t, bd)| b.observe("c", *t, FW, FH, bd))
        .map(|e| e.probability)
        .fold(0.0, f64::max);
    assert!(pa > 0.5 && pb < pa);
}

#[test]
fn standing_still_is_normal() {
    let mut p = engine();
    assert!(run(&mut p, &timeline(0.0, 600.0, 1.2, standing(500.0))).is_empty());
}

#[test]
fn two_people_are_tracked_apart() {
    let mut p = engine();
    let mut frames: Vec<(f64, Vec<Body>)> = Vec::new();
    let mut t = 0.0;
    while t <= 5.0 {
        frames.push((t, vec![standing(100.0), standing(900.0)]));
        t += 1.2;
    }
    while t <= 20.0 {
        frames.push((t, vec![standing(100.0), lying(820.0, false)]));
        t += 1.2;
    }
    let events: Vec<_> = frames
        .iter()
        .flat_map(|(t, b)| p.observe("cam", *t, FW, FH, b))
        .collect();
    assert_eq!(
        events
            .iter()
            .filter(|e| e.kind == PostureKind::Fall)
            .count(),
        1
    );
    assert_eq!(p.tracks("cam"), 2);
}

#[test]
fn hostile_input_is_ignored() {
    let mut p = engine();
    let bad = Body {
        x: f64::NAN,
        y: 1.0,
        w: 10.0,
        h: 10.0,
        score: 0.9,
        rest: false,
    };
    assert!(p.observe("cam", 1.0, FW, FH, &[bad]).is_empty());
    assert!(
        p.observe("bad camera!", 1.0, FW, FH, &[standing(1.0)])
            .is_empty()
    );
    assert!(
        p.observe("cam", f64::INFINITY, FW, FH, &[standing(1.0)])
            .is_empty()
    );
    assert!(p.observe("cam", 1.0, 0.0, FH, &[standing(1.0)]).is_empty());
    for i in 0..40 {
        let _ = p.observe(&format!("cam{i}"), 1.0, FW, FH, &[standing(1.0)]);
    }
    let many: Vec<Body> = (0..200).map(|i| standing(f64::from(i) * 7.0)).collect();
    let _ = p.observe("cam", 2.0, FW, FH, &many);
    assert!(p.tracks("cam") <= crate::posture::MAX_TRACKS);
    assert!(
        Posture::new(PostureConfig {
            immobile_s: 1.0,
            ..PostureConfig::default()
        })
        .is_none()
    );
}
