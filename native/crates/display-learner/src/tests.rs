use nuxiva_display_planner::Size;

use crate::context::{Activity, ContextVector, ScreenRole};
use crate::error::LearnError;
use crate::learner::{Learner, Outcome};
use crate::policy::LearnerPolicy;
use crate::signal::{FeedbackSample, Kind};

const ANNA: &str = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90";
const LUCA: &str = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0";
const DAY: u64 = 86_400_000;

fn ctx(band: u8) -> ContextVector {
    ContextVector {
        band,
        weekend: false,
        activity: Activity::Ambient,
        crowd: 1,
        role: ScreenRole::Main,
    }
}

fn sample(person: Option<&str>, widget: &str, kind: Kind, at_ms: u64) -> FeedbackSample {
    FeedbackSample {
        person: person.map(str::to_owned),
        widget: widget.to_owned(),
        kind,
        context: ctx(2),
        at_ms,
        cell: None,
        size: None,
        guests: false,
        urgency: 0,
    }
}

fn learner() -> Learner {
    match Learner::new(LearnerPolicy {
        explore_rate: 0.0,
        ..LearnerPolicy::default()
    }) {
        Ok(l) => l,
        Err(e) => unreachable!("{e}"),
    }
}

fn feed(l: &mut Learner, s: &FeedbackSample, times: u64) {
    for i in 0..times {
        let mut s = s.clone();
        s.at_ms = s.at_ms.saturating_add(i.saturating_mul(1000));
        assert!(l.observe(&s).is_ok());
    }
}

#[test]
fn quick_closes_push_the_preference_down_within_the_limit() {
    let mut l = learner();
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::QuickClose, 1000),
        200,
    );
    let a = l.affinity(Some(ANNA), "weather", &ctx(2), 300_000, 0, false);
    assert!(a.value < -0.25 && a.value >= -0.3, "{a:?}");
}

#[test]
fn explicit_requests_push_the_preference_up_within_the_limit() {
    let mut l = learner();
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::AskShow, 1000),
        200,
    );
    let a = l.affinity(Some(ANNA), "weather", &ctx(2), 300_000, 0, false);
    assert!(a.value > 0.25 && a.value <= 0.3, "{a:?}");
}

#[test]
fn safety_widgets_and_urgent_samples_never_learn() {
    let mut l = learner();
    let s = sample(Some(ANNA), "alarm", Kind::QuickClose, 1000);
    assert_eq!(l.observe(&s), Ok(Outcome::Ignored));
    let mut urgent = sample(Some(ANNA), "weather", Kind::QuickClose, 1000);
    urgent.urgency = 3;
    assert_eq!(l.observe(&urgent), Ok(Outcome::Ignored));
    assert!(
        l.affinity(Some(ANNA), "alarm", &ctx(2), 2000, 0, false)
            .value
            .abs()
            < f32::EPSILON
    );
    assert!(
        l.affinity(Some(ANNA), "weather", &ctx(2), 2000, 0, false)
            .value
            .abs()
            < f32::EPSILON
    );
}

#[test]
fn guests_only_touch_the_session_profile() {
    let mut l = learner();
    let mut s = sample(Some(ANNA), "music", Kind::QuickClose, 1000);
    s.guests = true;
    feed(&mut l, &s, 20);
    assert!(l.take_dirty().is_empty());
    assert!(l.persons().is_empty());
    assert!(l.affinity(None, "music", &ctx(2), 30_000, 0, true).value < 0.0);
    l.forget_session();
    assert!(
        l.affinity(None, "music", &ctx(2), 30_000, 0, true)
            .value
            .abs()
            < f32::EPSILON
    );
}

#[test]
fn people_do_not_share_preferences() {
    let mut l = learner();
    feed(
        &mut l,
        &sample(Some(ANNA), "news_feed", Kind::QuickClose, 1000),
        50,
    );
    assert!(
        l.affinity(Some(LUCA), "news_feed", &ctx(2), 60_000, 0, false)
            .value
            .abs()
            < f32::EPSILON
    );
    assert_eq!(l.take_dirty(), vec![ANNA.to_owned()]);
}

#[test]
fn the_context_changes_the_answer() {
    let mut l = learner();
    let mut morning = sample(Some(ANNA), "weather", Kind::AskShow, 1000);
    morning.context = ctx(1);
    let mut night = sample(Some(ANNA), "weather", Kind::QuickClose, 1000);
    night.context = ctx(5);
    feed(&mut l, &morning, 60);
    feed(&mut l, &night, 60);
    let am = l
        .affinity(Some(ANNA), "weather", &ctx(1), 100_000, 0, false)
        .value;
    let pm = l
        .affinity(Some(ANNA), "weather", &ctx(5), 100_000, 0, false)
        .value;
    assert!(am > 0.0 && pm < 0.0 && am - pm > 0.1, "{am} {pm}");
}

#[test]
fn old_habits_fade_with_the_half_life() {
    let mut l = learner();
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::QuickClose, 1000),
        30,
    );
    let fresh = l
        .affinity(Some(ANNA), "weather", &ctx(2), 40_000, 0, false)
        .value;
    let old = l
        .affinity(Some(ANNA), "weather", &ctx(2), 210 * DAY, 0, false)
        .value;
    assert!(fresh < -0.15 && old.abs() < 0.02, "{fresh} {old}");
}

#[test]
fn exploration_stays_rare_and_never_with_guests_or_work_widgets() {
    let Ok(mut l) = Learner::new(LearnerPolicy::default()) else {
        unreachable!()
    };
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::Interact, 1000),
        3,
    );
    feed(
        &mut l,
        &sample(Some(ANNA), "active_tasks", Kind::Interact, 1000),
        3,
    );
    let explored = (0..20_000_u64)
        .filter(|t| {
            l.affinity(Some(ANNA), "weather", &ctx(2), 10_000, *t, false)
                .explored
        })
        .count();
    assert!((600..=1400).contains(&explored), "{explored}");
    assert!((0..5000_u64).all(|t| {
        !l.affinity(Some(ANNA), "weather", &ctx(2), 10_000, t, true)
            .explored
    }));
    assert!((0..5000_u64).all(|t| {
        !l.affinity(Some(ANNA), "active_tasks", &ctx(2), 10_000, t, false)
            .explored
    }));
    assert!((0..5000_u64).all(|t| {
        l.affinity(Some(ANNA), "weather", &ctx(2), 10_000, t, false)
            .value
            <= 0.3
    }));
}

#[test]
fn repeated_moves_become_a_placement_hint() {
    let mut l = learner();
    let mut s = sample(Some(ANNA), "weather", Kind::Move, 1000);
    s.cell = Some([8, 0]);
    s.size = Some(Size::L);
    assert!(l.observe(&s).is_ok());
    assert_eq!(
        l.placement(Some(ANNA), "weather", ScreenRole::Main, 2000),
        (None, None)
    );
    assert!(l.observe(&s).is_ok());
    assert_eq!(
        l.placement(Some(ANNA), "weather", ScreenRole::Main, 3000),
        (Some([8, 0]), Some(Size::L))
    );
    assert_eq!(
        l.placement(Some(ANNA), "weather", ScreenRole::Side, 3000),
        (None, None)
    );
}

#[test]
fn reset_forgets_one_person() {
    let mut l = learner();
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::QuickClose, 1000),
        10,
    );
    feed(
        &mut l,
        &sample(Some(LUCA), "weather", Kind::QuickClose, 1000),
        10,
    );
    assert_eq!(l.reset(ANNA), Ok(true));
    assert_eq!(l.persons(), vec![LUCA.to_owned()]);
    assert_eq!(l.reset("nope"), Err(LearnError::InvalidPerson));
}

#[test]
fn profiles_round_trip_and_reject_tampering() {
    let mut l = learner();
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::AskShow, 1000),
        10,
    );
    let Ok(raw) = l.export(ANNA) else {
        unreachable!()
    };
    let mut other = learner();
    assert!(other.import(ANNA, &raw).is_ok());
    let a = l.affinity(Some(ANNA), "weather", &ctx(2), 20_000, 0, false);
    let b = other.affinity(Some(ANNA), "weather", &ctx(2), 20_000, 0, false);
    assert!((a.value - b.value).abs() < 1e-6);
    let bad = String::from_utf8_lossy(&raw).replace("weather", "WEATHER!");
    assert_eq!(other.import(LUCA, bad.as_bytes()), Err(LearnError::Corrupt));
    assert_eq!(
        other.import(
            LUCA,
            b"{\"models\":{\"x\":{\"reward\":[1],\"weight\":[1],\"at_ms\":0}}}"
        ),
        Err(LearnError::Corrupt)
    );
    assert_eq!(other.import(LUCA, b"not json"), Err(LearnError::Corrupt));
}

#[test]
fn inputs_are_validated() {
    let mut l = learner();
    assert_eq!(
        l.observe(&sample(Some("short"), "weather", Kind::Interact, 1)),
        Err(LearnError::InvalidPerson)
    );
    assert_eq!(
        l.observe(&sample(Some(ANNA), "../etc", Kind::Interact, 1)),
        Err(LearnError::InvalidWidget)
    );
    let mut s = sample(Some(ANNA), "weather", Kind::Move, 1);
    s.cell = Some([12, 0]);
    assert_eq!(l.observe(&s), Err(LearnError::InvalidSample));
    assert!(
        LearnerPolicy {
            limit: 0.5,
            ..LearnerPolicy::default()
        }
        .validate()
        .is_err()
    );
    assert!(
        LearnerPolicy {
            explore_rate: 0.1,
            ..LearnerPolicy::default()
        }
        .validate()
        .is_err()
    );
    assert!(
        LearnerPolicy {
            half_life_ms: 1,
            ..LearnerPolicy::default()
        }
        .validate()
        .is_err()
    );
}

#[test]
fn the_number_of_people_is_bounded() {
    let Ok(mut l) = Learner::new(LearnerPolicy {
        max_persons: 1,
        ..LearnerPolicy::default()
    }) else {
        unreachable!()
    };
    assert!(
        l.observe(&sample(Some(ANNA), "weather", Kind::Interact, 1))
            .is_ok()
    );
    assert_eq!(
        l.observe(&sample(Some(LUCA), "weather", Kind::Interact, 1)),
        Err(LearnError::Capacity)
    );
}

#[test]
fn models_per_person_are_bounded_by_evicting_the_oldest() {
    let Ok(mut l) = Learner::new(LearnerPolicy {
        max_models: 2,
        explore_rate: 0.0,
        ..LearnerPolicy::default()
    }) else {
        unreachable!()
    };
    assert!(
        l.observe(&sample(Some(ANNA), "weather", Kind::Interact, 1))
            .is_ok()
    );
    assert!(
        l.observe(&sample(Some(ANNA), "music", Kind::Interact, 2))
            .is_ok()
    );
    assert!(
        l.observe(&sample(Some(ANNA), "clock", Kind::Interact, 3))
            .is_ok()
    );
    assert!(
        l.affinity(Some(ANNA), "weather", &ctx(2), 4, 0, false)
            .value
            .abs()
            < f32::EPSILON
    );
    assert!(l.affinity(Some(ANNA), "clock", &ctx(2), 4, 0, false).value > 0.0);
}

#[test]
fn metrics_count_what_happened() {
    let mut l = learner();
    feed(&mut l, &sample(Some(ANNA), "weather", Kind::Shown, 1000), 4);
    feed(
        &mut l,
        &sample(Some(ANNA), "weather", Kind::QuickClose, 1000),
        1,
    );
    let Some(m) = l.metrics(Some(ANNA)) else {
        unreachable!()
    };
    assert!((m.shown - 4.0).abs() < 0.01 && (m.quick_close - 1.0).abs() < 0.01);
    assert!(l.metrics(Some(LUCA)).is_none());
}
