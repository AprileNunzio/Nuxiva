use crate::GestureEngine;
use crate::error::GestureError;
use crate::events::{DuoPhase, GestureEvent, PointerPhase};
use crate::gesture::{DuoMotion, GestureKind};
use crate::landmarks::fixtures::{hand_with, shaped};
use crate::landmarks::{Frame, Hand, Handedness, Point};
use crate::pose::Pose;
use crate::profile::{Binding, GestureProfile, HandFilter};
use std::collections::BTreeMap;

fn grip(x: f32, y: f32, closed: bool, handedness: Handedness) -> Result<Hand, GestureError> {
    let gap = if closed { 0.01 } else { 0.2 };
    hand_with(
        &[
            (0, Point::new(x, y + 0.3)),
            (9, Point::new(x, y + 0.1)),
            (4, Point::new(x - gap / 2.0, y)),
            (8, Point::new(x + gap / 2.0, y)),
        ],
        handedness,
    )
}

fn feed_all(
    engine: &mut GestureEngine,
    frames: Vec<(u64, Vec<Hand>)>,
    context: &str,
) -> Result<Vec<GestureEvent>, GestureError> {
    let mut out = Vec::new();
    for (t, hands) in frames {
        out.extend(engine.feed(&Frame::new(t, hands)?, context));
    }
    Ok(out)
}

fn actions(events: &[GestureEvent]) -> Vec<String> {
    events
        .iter()
        .filter_map(|e| match e {
            GestureEvent::Action { action, .. } => Some(action.clone()),
            _ => None,
        })
        .collect()
}

fn unmirrored() -> GestureProfile {
    GestureProfile {
        mirror: false,
        ..GestureProfile::default()
    }
}

fn binding(gesture: GestureKind, context: &str, modifier: Option<Pose>, action: &str) -> Binding {
    Binding {
        gesture,
        hand: HandFilter::Any,
        context: context.to_owned(),
        modifier,
        action: action.to_owned(),
        args: BTreeMap::new(),
        confirm: false,
        enabled: true,
    }
}

#[test]
fn pinch_drives_pointer_and_tap_binding() -> Result<(), GestureError> {
    let mut profile = unmirrored();
    profile.bindings = vec![binding(GestureKind::Tap, "*", None, "ui.click")];
    let mut engine = GestureEngine::new(profile);
    let r = Handedness::Right;
    let events = feed_all(
        &mut engine,
        vec![
            (0, vec![grip(0.5, 0.4, false, r)?]),
            (30, vec![grip(0.5, 0.4, true, r)?]),
            (60, vec![grip(0.5, 0.4, true, r)?]),
            (90, vec![grip(0.5, 0.4, false, r)?]),
            (120, vec![grip(0.5, 0.4, false, r)?]),
        ],
        "desktop",
    )?;
    let phases: Vec<PointerPhase> = events
        .iter()
        .filter_map(|e| match e {
            GestureEvent::Pointer { phase, .. } => Some(*phase),
            _ => None,
        })
        .collect();
    assert!(phases.contains(&PointerPhase::Down) && phases.contains(&PointerPhase::Up));
    assert_eq!(actions(&events), vec!["ui.click".to_owned()]);
    Ok(())
}

#[test]
fn two_hand_pinch_spread_fires_duo() -> Result<(), GestureError> {
    let mut profile = unmirrored();
    profile.bindings = vec![binding(
        GestureKind::Duo(DuoMotion::Spread),
        "*",
        None,
        "view.zoom_in",
    )];
    let mut engine = GestureEngine::new(profile);
    let mut frames = Vec::new();
    for i in 0..12_u16 {
        let half = 0.1 + f32::from(i) * 0.03;
        frames.push((
            u64::from(i) * 33,
            vec![
                grip(0.5 - half, 0.4, true, Handedness::Left)?,
                grip(0.5 + half, 0.4, true, Handedness::Right)?,
            ],
        ));
    }
    frames.push((
        500,
        vec![
            grip(0.2, 0.4, false, Handedness::Left)?,
            grip(0.8, 0.4, false, Handedness::Right)?,
        ],
    ));
    let events = feed_all(&mut engine, frames, "desktop")?;
    let duo_phases: Vec<DuoPhase> = events
        .iter()
        .filter_map(|e| match e {
            GestureEvent::Duo { phase, .. } => Some(*phase),
            _ => None,
        })
        .collect();
    assert_eq!(duo_phases.first(), Some(&DuoPhase::Start));
    assert_eq!(duo_phases.last(), Some(&DuoPhase::End));
    assert!(actions(&events).contains(&"view.zoom_in".to_owned()));
    Ok(())
}

#[test]
fn held_open_palm_triggers_default_listen() -> Result<(), GestureError> {
    let mut engine = GestureEngine::new(GestureProfile {
        pointer: false,
        ..unmirrored()
    });
    let palm = shaped([true; 5], Point::new(0.5, 0.5), Handedness::Right)?;
    let frames = (0..30_u16)
        .map(|i| (u64::from(i) * 40, vec![palm.clone()]))
        .collect();
    let events = feed_all(&mut engine, frames, "desktop")?;
    assert_eq!(actions(&events), vec!["assistant.listen".to_owned()]);
    Ok(())
}

#[test]
fn context_and_modifier_pick_most_specific() -> Result<(), GestureError> {
    let mut profile = GestureProfile {
        pointer: false,
        ..unmirrored()
    };
    profile.bindings = vec![
        binding(GestureKind::Hold(Pose::Point), "*", None, "generic"),
        binding(GestureKind::Hold(Pose::Point), "tv", None, "tv.only"),
        binding(
            GestureKind::Hold(Pose::Point),
            "tv",
            Some(Pose::Fist),
            "tv.with_fist",
        ),
    ];
    let point = shaped(
        [false, true, false, false, false],
        Point::new(0.7, 0.5),
        Handedness::Right,
    )?;
    let fist = shaped([false; 5], Point::new(0.3, 0.5), Handedness::Left)?;
    let run = |context: &str, with_fist: bool| -> Result<Vec<String>, GestureError> {
        let mut engine = GestureEngine::new(profile.clone());
        let frames = (0..30_u16)
            .map(|i| {
                let hands = if with_fist {
                    vec![point.clone(), fist.clone()]
                } else {
                    vec![point.clone()]
                };
                (u64::from(i) * 40, hands)
            })
            .collect();
        Ok(actions(&feed_all(&mut engine, frames, context)?))
    };
    assert_eq!(run("desktop", false)?, vec!["generic".to_owned()]);
    assert_eq!(run("tv", false)?, vec!["tv.only".to_owned()]);
    assert!(run("tv", true)?.contains(&"tv.with_fist".to_owned()));
    Ok(())
}

#[test]
fn lost_hands_hide_pointer() -> Result<(), GestureError> {
    let mut engine = GestureEngine::new(unmirrored());
    let events = feed_all(
        &mut engine,
        vec![
            (0, vec![grip(0.5, 0.4, false, Handedness::Right)?]),
            (900, vec![]),
        ],
        "desktop",
    )?;
    assert!(matches!(
        events.last(),
        Some(GestureEvent::Pointer {
            phase: PointerPhase::Hidden,
            ..
        })
    ));
    Ok(())
}
