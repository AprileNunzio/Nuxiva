use crate::{Cadence, Lifecycle, Policy, Scheduler, SchedulerError, WidgetInput};

pub fn widget(instance: &str, cadence: Cadence, cost_mb: f32) -> WidgetInput {
    WidgetInput {
        instance: instance.to_owned(),
        widget: instance.split('@').next().unwrap_or(instance).to_owned(),
        cadence,
        cost_mb,
    }
}

#[test]
fn cadence_is_inferred_from_the_manifest_refresh() {
    assert_eq!(Cadence::infer(None), Cadence::Static);
    assert_eq!(Cadence::infer(Some(0.2)), Cadence::Realtime);
    assert_eq!(Cadence::infer(Some(1.0)), Cadence::Live);
    assert_eq!(Cadence::infer(Some(30.0)), Cadence::Fresh);
    assert_eq!(Cadence::infer(Some(900.0)), Cadence::Slow);
    assert_eq!(Cadence::infer(Some(f64::NAN)), Cadence::Static);
}

#[test]
fn planned_widgets_start_warm_and_go_live_when_seen() {
    let mut s = Scheduler::new(Policy::default());
    let added = s.admit(0, &[widget("weather@1", Cadence::Slow, 4.0)], 0);
    assert_eq!(added.map(|t| t.len()), Ok(1));
    assert_eq!(s.state("weather@1"), Some(Lifecycle::Warm));
    assert!(s.visibility("weather@1", true, 10).is_ok());
    assert_eq!(s.state("weather@1"), Some(Lifecycle::Live));
    assert!(s.visibility("weather@1", false, 20).is_ok());
    assert_eq!(s.state("weather@1"), Some(Lifecycle::Frozen));
}

#[test]
fn widgets_dropped_from_the_plan_are_forgotten() {
    let mut s = Scheduler::new(Policy::default());
    assert!(
        s.admit(
            0,
            &[
                widget("a@1", Cadence::Live, 1.0),
                widget("b@1", Cadence::Live, 1.0)
            ],
            0
        )
        .is_ok()
    );
    let moved = s
        .admit(0, &[widget("a@1", Cadence::Live, 1.0)], 5)
        .unwrap_or_default();
    assert_eq!(moved.len(), 1);
    assert_eq!(moved.first().map(|t| t.to), Some(Lifecycle::Dormant));
    assert_eq!(s.state("b@1"), None);
}

#[test]
fn other_screens_are_left_alone() {
    let mut s = Scheduler::new(Policy::default());
    assert!(s.admit(0, &[widget("a@1", Cadence::Live, 1.0)], 0).is_ok());
    assert!(s.admit(1, &[], 0).is_ok());
    assert_eq!(s.state("a@1"), Some(Lifecycle::Warm));
}

#[test]
fn frozen_widgets_hibernate_after_a_while() {
    let mut s = Scheduler::new(Policy::default());
    assert!(s.admit(0, &[widget("a@1", Cadence::Live, 1.0)], 0).is_ok());
    assert!(s.visibility("a@1", true, 0).is_ok());
    assert!(s.visibility("a@1", false, 1_000).is_ok());
    let (_, moved) = s.tick(1_000 + Policy::default().hibernate_after_ms);
    assert_eq!(moved.first().map(|t| t.to), Some(Lifecycle::Hibernated));
}

#[test]
fn live_widgets_refresh_at_their_cadence() {
    let mut s = Scheduler::new(Policy::default());
    assert!(
        s.admit(
            0,
            &[
                widget("music@1", Cadence::Live, 1.0),
                widget("doc@1", Cadence::Static, 1.0)
            ],
            0
        )
        .is_ok()
    );
    assert!(s.visibility("music@1", true, 0).is_ok());
    assert!(s.tick(500).0.is_empty());
    let (due, _) = s.tick(1_000);
    assert_eq!(
        due.iter().map(|d| d.instance.as_str()).collect::<Vec<_>>(),
        vec!["music@1"]
    );
    assert!(s.tick(1_500).0.is_empty());
    assert_eq!(s.tick(2_000).0.len(), 1);
}

#[test]
fn warm_widgets_refresh_slower_than_live_ones() {
    let mut s = Scheduler::new(Policy::default());
    assert!(
        s.admit(0, &[widget("music@1", Cadence::Live, 1.0)], 0)
            .is_ok()
    );
    assert!(s.tick(1_000).0.is_empty());
    assert_eq!(s.tick(10_000).0.len(), 1);
}

#[test]
fn an_empty_room_freezes_then_puts_everything_to_sleep() {
    let mut s = Scheduler::new(Policy::default());
    assert!(
        s.admit(0, &[widget("health@1", Cadence::Fresh, 3.0)], 0)
            .is_ok()
    );
    assert!(s.visibility("health@1", true, 0).is_ok());
    let away = s.audience(0, true, 100);
    assert_eq!(away.first().map(|t| t.to), Some(Lifecycle::Frozen));
    assert_eq!(s.visibility("health@1", true, 200).map(|t| t.len()), Ok(0));
    let (_, slept) = s.tick(100 + Policy::default().sleep_grace_ms);
    assert_eq!(slept.first().map(|t| t.to), Some(Lifecycle::Dormant));
    assert!(s.tick(1_000_000).0.is_empty());
    let back = s.audience(0, false, 2_000_000);
    assert_eq!(back.first().map(|t| t.to), Some(Lifecycle::Warm));
}

#[test]
fn widgets_planned_while_nobody_is_there_stay_dormant() {
    let mut s = Scheduler::new(Policy::default());
    let _ = s.audience(0, true, 0);
    assert!(s.admit(0, &[widget("a@1", Cadence::Live, 1.0)], 10).is_ok());
    assert_eq!(s.state("a@1"), Some(Lifecycle::Dormant));
}

#[test]
fn bad_input_is_rejected() {
    let mut s = Scheduler::new(Policy::default());
    assert_eq!(
        s.admit(0, &[widget("bad id", Cadence::Live, 1.0)], 0),
        Err(SchedulerError::InstanceId)
    );
    assert_eq!(
        s.admit(0, &[widget("a@1", Cadence::Live, f32::NAN)], 0),
        Err(SchedulerError::Cost)
    );
    assert_eq!(
        s.visibility("missing", true, 0),
        Err(SchedulerError::UnknownInstance)
    );
    let small = Policy {
        max_widgets: 1,
        ..Policy::default()
    };
    let mut s = Scheduler::new(small);
    assert_eq!(
        s.admit(
            0,
            &[
                widget("a@1", Cadence::Live, 1.0),
                widget("b@1", Cadence::Live, 1.0)
            ],
            0
        ),
        Err(SchedulerError::TooManyWidgets)
    );
}
