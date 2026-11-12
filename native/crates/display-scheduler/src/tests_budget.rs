use crate::tests::widget;
use crate::{Cadence, Lifecycle, Policy, Scheduler};

#[test]
fn measured_costs_are_smoothed() {
    let mut s = Scheduler::new(Policy::default());
    assert!(s.admit(0, &[widget("a@1", Cadence::Live, 10.0)], 0).is_ok());
    assert!(s.visibility("a@1", true, 0).is_ok());
    assert!(s.observe("a@1", 20.0).is_ok());
    let cost = s.screen_cost(0);
    assert!(cost > 10.0 && cost < 20.0);
    assert!(s.observe("a@1", -1.0).is_err());
}

#[test]
fn pressure_hibernates_the_heaviest_frozen_widgets_first() {
    let mut s = Scheduler::new(Policy::default());
    let plan = [
        widget("big@1", Cadence::Live, 50.0),
        widget("small@1", Cadence::Live, 5.0),
        widget("seen@1", Cadence::Live, 20.0),
    ];
    assert!(s.admit(0, &plan, 0).is_ok());
    for id in ["big@1", "small@1", "seen@1"] {
        assert!(s.visibility(id, true, 0).is_ok());
    }
    assert!(s.visibility("big@1", false, 1).is_ok());
    assert!(s.visibility("small@1", false, 1).is_ok());
    let moved = s.pressure(0, 30.0, 2);
    assert_eq!(
        moved
            .iter()
            .map(|t| t.instance.as_str())
            .collect::<Vec<_>>(),
        vec!["big@1"]
    );
    assert_eq!(s.state("seen@1"), Some(Lifecycle::Live));
    assert_eq!(s.state("small@1"), Some(Lifecycle::Frozen));
}

#[test]
fn a_crashing_widget_is_quarantined_on_every_screen() {
    let mut s = Scheduler::new(Policy::default());
    assert!(
        s.admit(0, &[widget("chart@1", Cadence::Live, 1.0)], 0)
            .is_ok()
    );
    assert!(
        s.admit(1, &[widget("chart@2", Cadence::Live, 1.0)], 0)
            .is_ok()
    );
    assert_eq!(s.error("chart@1", 10).map(|t| t.len()), Ok(0));
    assert_eq!(s.error("chart@1", 20).map(|t| t.len()), Ok(0));
    assert_eq!(s.error("chart@1", 30).map(|t| t.len()), Ok(2));
    assert_eq!(s.quarantined(40), vec!["chart".to_owned()]);
    assert!(
        s.admit(0, &[widget("chart@3", Cadence::Live, 1.0)], 50)
            .is_ok()
    );
    assert_eq!(s.state("chart@3"), None);
    let later = 30 + Policy::default().quarantine_ms + 1;
    let _ = s.tick(later);
    assert!(
        s.admit(0, &[widget("chart@3", Cadence::Live, 1.0)], later)
            .is_ok()
    );
    assert_eq!(s.state("chart@3"), Some(Lifecycle::Warm));
}

#[test]
fn old_errors_do_not_count() {
    let mut s = Scheduler::new(Policy::default());
    assert!(
        s.admit(0, &[widget("chart@1", Cadence::Live, 1.0)], 0)
            .is_ok()
    );
    let window = Policy::default().error_window_ms;
    for k in 0..5u64 {
        assert_eq!(s.error("chart@1", k * (window + 1)).map(|t| t.len()), Ok(0));
    }
}
