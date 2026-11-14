use std::time::{Duration, Instant};

use crate::{Critic, ErrorBus, ErrorPayload, Remedy, Settings};

fn payload(component: &str, code: &str) -> ErrorPayload {
    let bus = ErrorBus::new(4);
    bus.report(component, code, "ctx");
    bus.drain().remove(0)
}

#[test]
fn queue_errors_get_task_remedies_and_escalate_to_the_user() {
    let settings = Settings {
        critic_threshold: 3,
        critic_window_ms: 1_000,
        ..Settings::default()
    };
    let mut critic = Critic::new(&settings);
    let start = Instant::now();
    assert_eq!(
        critic.advise(&payload("queue:t1", "queue.crashed"), start),
        Some(Remedy::RestartTask("t1".into()))
    );
    for n in 0..2 {
        assert_eq!(
            critic.advise(
                &payload("queue:t1", "queue.transient"),
                start + Duration::from_millis(n)
            ),
            Some(Remedy::RetryWithBackoff("t1".into()))
        );
    }
    assert_eq!(
        critic.advise(
            &payload("queue:t1", "queue.transient"),
            start + Duration::from_millis(3)
        ),
        Some(Remedy::EscalateToUser("t1".into()))
    );
    assert_eq!(
        critic.advise(&payload("queue:t2", "queue.policy"), start),
        Some(Remedy::EscalateToUser("t2".into()))
    );
    assert_eq!(critic.advise(&payload("queue:t3", "other"), start), None);
    assert_eq!(
        critic.advise(&payload("queue:", "queue.fatal"), start),
        None
    );
}
