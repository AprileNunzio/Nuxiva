use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};

use nuxiva_display_scheduler::Policy;
use serde_json::json;

use crate::engine::{Clock, Engine};
use crate::protocol::Request;

#[derive(Debug, Clone, Default)]
struct FakeClock(Arc<AtomicU64>);

impl Clock for FakeClock {
    fn now_ms(&self) -> u64 {
        self.0.load(Ordering::SeqCst)
    }
}

fn request(value: serde_json::Value) -> Request {
    serde_json::from_value(value).unwrap_or(Request::Ping {})
}

#[test]
fn the_engine_runs_the_widget_lifecycle() {
    let clock = FakeClock::default();
    let mut engine = Engine::new(Policy::default(), clock.clone());
    let admitted = engine.handle(request(json!({"op": "admit", "screen": 0,
        "widgets": [{"instance": "music@1", "widget": "music", "cadence": "live", "cost_mb": 2.0}]})));
    assert_eq!(
        admitted
            .ok()
            .and_then(|v| v.pointer("/transitions/0/to")?.as_str().map(str::to_owned)),
        Some("warm".to_owned())
    );
    let seen = engine.handle(request(
        json!({"op": "visibility", "instance": "music@1", "visible": true}),
    ));
    assert_eq!(
        seen.ok()
            .and_then(|v| v.pointer("/transitions/0/to")?.as_str().map(str::to_owned)),
        Some("live".to_owned())
    );
    clock.0.store(1_000, Ordering::SeqCst);
    let tick = engine.handle(request(json!({"op": "tick"})));
    assert_eq!(
        tick.ok()
            .and_then(|v| v.pointer("/due/0/instance")?.as_str().map(str::to_owned)),
        Some("music@1".to_owned())
    );
}

#[test]
fn unknown_instances_return_a_typed_error() {
    let mut engine = Engine::new(Policy::default(), FakeClock::default());
    let out = engine.handle(request(
        json!({"op": "visibility", "instance": "nope", "visible": true}),
    ));
    assert_eq!(
        out.err().map(|e| e.code()),
        Some("display.scheduler.unknown_instance")
    );
}

#[test]
fn unknown_fields_are_refused() {
    let parsed: Result<Request, _> = serde_json::from_value(json!({"op": "tick", "extra": 1}));
    assert!(parsed.is_err());
}

#[test]
fn diffs_are_served_by_the_daemon() {
    let mut engine = Engine::new(Policy::default(), FakeClock::default());
    let out = engine.handle(request(
        json!({"op": "diff", "old": {"a": 1}, "new": {"a": 2}}),
    ));
    assert_eq!(
        out.ok().and_then(|v| v.pointer("/ops/0/op").cloned()),
        Some(json!("replace"))
    );
}
