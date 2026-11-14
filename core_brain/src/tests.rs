use std::sync::Arc;
use std::time::Duration;

use nuxiva_context_core::{ContextSettings, Delta, PersonId, Sealer, SharedContext};
use nuxiva_ear_core::VoicePolicy;

use crate::{
    BrainError, BrainResult, Decision, Embedder, Event, Frame, GateVerdict, Gatekeeper, HotMemory,
    Layer, SensoryPipeline, SharedPipeline, Supervisor, SupervisorConfig,
};

struct Fixed(Vec<f32>);

impl Embedder for Fixed {
    fn embed(&self, _pcm: &[f32]) -> BrainResult<Vec<f32>> {
        Ok(self.0.clone())
    }
}

struct Failing;

impl Embedder for Failing {
    fn embed(&self, _pcm: &[f32]) -> BrainResult<Vec<f32>> {
        Err(BrainError::Embedding("model"))
    }
}

fn memory() -> HotMemory {
    let sealer = Sealer::random().expect("sealer");
    HotMemory::new(SharedContext::new(ContextSettings::default(), sealer).expect("ctx"))
}

fn voice(seed: f32) -> Vec<f32> {
    vec![seed, 1.0 - seed, 0.25, 0.5]
}

fn pipeline(embedder: Arc<dyn Embedder>) -> SensoryPipeline {
    SensoryPipeline::new(
        embedder,
        Gatekeeper::new(["nuxiva"]),
        VoicePolicy::default(),
    )
}

fn frame(text: &str, at_ms: u64) -> Frame {
    let near: Vec<f32> = (0..1_600_u16)
        .map(|i| (f32::from(i) * 0.05).sin() * 0.3)
        .collect();
    Frame {
        far: vec![0.0; near.len()],
        near,
        transcript: text.to_owned(),
        at_ms,
    }
}

#[test]
fn gate_requires_name_or_verified_follow_up() {
    let gate = Gatekeeper::new(["Nuxiva"]);
    assert_eq!(
        gate.judge("Ehi Nuxiva, che ore sono", false, None),
        GateVerdict::Address
    );
    assert!(matches!(
        gate.judge("che ore sono", false, Some(100)),
        GateVerdict::Ignore(_)
    ));
    assert_eq!(
        gate.judge("accendi la luce", true, Some(4_000)),
        GateVerdict::Address
    );
    assert!(matches!(
        gate.judge("accendi la luce", true, Some(60_000)),
        GateVerdict::Ignore(_)
    ));
    assert!(matches!(
        gate.judge("bella giornata", true, Some(1_000)),
        GateVerdict::Ignore(_)
    ));
    assert!(matches!(
        gate.judge("a", true, Some(1)),
        GateVerdict::Ignore("too_short")
    ));
    assert!(matches!(
        gate.judge(&"x".repeat(3_000), true, None),
        GateVerdict::Ignore("too_long")
    ));
}

#[test]
fn gate_ignores_control_characters_in_names() {
    let gate = Gatekeeper::new(["nuxiva"]);
    assert_eq!(
        gate.judge("nux\u{0}iva accendi", false, None),
        GateVerdict::Ignore("not_addressed_unverified")
    );
}

#[test]
fn pipeline_rejects_echo_only_and_bad_frames() {
    let mut p = pipeline(Arc::new(Fixed(voice(0.9))));
    let mut silent = frame("nuxiva", 0);
    silent.near = vec![0.0; 1_600];
    assert_eq!(
        p.process(&silent).expect("ok"),
        Decision::Rejected {
            layer: Layer::Aec,
            reason: "echo_only"
        }
    );
    let mut bad = frame("nuxiva", 0);
    bad.far.pop();
    assert_eq!(p.process(&bad), Err(BrainError::Input("length")));
    let mut empty = frame("nuxiva", 0);
    empty.near.clear();
    empty.far.clear();
    assert_eq!(p.process(&empty), Err(BrainError::Input("empty")));
}

#[test]
fn pipeline_without_enrolment_uses_gatekeeper_only() {
    let mut p = pipeline(Arc::new(Failing));
    let out = p.process(&frame("nuxiva accendi la luce", 10)).expect("ok");
    assert!(matches!(out, Decision::Accepted { speaker: None, .. }));
    let out = p.process(&frame("accendi la luce", 20)).expect("ok");
    assert!(matches!(
        out,
        Decision::Rejected {
            layer: Layer::Gatekeeper,
            ..
        }
    ));
}

#[test]
fn pipeline_biometry_accepts_owner_and_rejects_stranger() {
    let mut p = pipeline(Arc::new(Fixed(voice(0.9))));
    p.enroll("nunzio", &[voice(0.9), voice(0.88)])
        .expect("enrol");
    let out = p.process(&frame("nuxiva accendi la luce", 10)).expect("ok");
    assert!(
        matches!(&out, Decision::Accepted { speaker, .. } if speaker.as_deref() == Some("nunzio"))
    );
    let follow = p.process(&frame("spegni la luce", 2_000)).expect("ok");
    assert!(matches!(follow, Decision::Accepted { .. }));

    let mut q = pipeline(Arc::new(Fixed(vec![-0.9, 0.1, -0.25, -0.5])));
    q.enroll("nunzio", &[voice(0.9), voice(0.88)])
        .expect("enrol");
    let out = q.process(&frame("nuxiva accendi la luce", 10)).expect("ok");
    assert!(matches!(
        out,
        Decision::Rejected {
            layer: Layer::Biometry,
            ..
        }
    ));
}

#[test]
fn pipeline_surfaces_embedder_failure() {
    let mut p = pipeline(Arc::new(Failing));
    p.enroll("nunzio", &[voice(0.9)]).expect("enrol");
    assert_eq!(
        p.process(&frame("nuxiva", 1)),
        Err(BrainError::Embedding("model"))
    );
}

#[test]
fn enrol_rejects_invalid_slug() {
    let mut p = pipeline(Arc::new(Fixed(voice(0.9))));
    assert!(p.enroll("Bad Slug", &[voice(0.9)]).is_err());
    assert!(p.enroll("ok", &[]).is_err());
}

#[tokio::test]
async fn memory_tracks_turns_and_deltas() {
    let mem = memory();
    assert!(mem.listening().await);
    mem.register_turn(Some(PersonId::new("nunzio").expect("id")), 50)
        .await;
    mem.register_turn(None, 10).await;
    assert_eq!(mem.turns().await, 2);
    assert_eq!(mem.last_utterance_ms().await, 50);
    assert!(mem.active().await.is_none());
    mem.set_listening(false).await;
    assert!(!mem.listening().await);
    let version = mem
        .apply(Delta::SetPresence {
            present: vec![],
            at_ms: 5,
        })
        .await
        .expect("apply");
    assert_eq!(mem.snapshot().await.version(), version);
}

#[tokio::test]
async fn memory_serves_concurrent_readers_during_writes() {
    let mem = memory();
    let mut tasks = Vec::new();
    for i in 0..32_u64 {
        let m = mem.clone();
        tasks.push(tokio::spawn(async move {
            m.register_turn(None, i).await;
            m.snapshot().await.version()
        }));
    }
    for t in tasks {
        t.await.expect("join");
    }
    assert_eq!(mem.turns().await, 32);
}

#[tokio::test]
async fn supervisor_emits_events_and_updates_memory() {
    let mem = memory();
    let mut p = pipeline(Arc::new(Fixed(voice(0.9))));
    p.enroll("nunzio", &[voice(0.9)]).expect("enrol");
    let (sup, mut events) = Supervisor::start(
        SharedPipeline::new(p),
        mem.clone(),
        SupervisorConfig::default(),
    );
    sup.submit(frame("nuxiva accendi la luce", 100))
        .expect("submit");
    sup.submit(frame("rumore di sottofondo senza senso", 9_999_999))
        .expect("submit");
    let first = events.recv().await.expect("event");
    assert!(matches!(first, Event::Heard { .. }));
    let second = events.recv().await.expect("event");
    assert!(matches!(
        second,
        Event::Dropped {
            layer: Layer::Gatekeeper,
            ..
        }
    ));
    assert_eq!(mem.turns().await, 1);
    assert_eq!(mem.active().await.expect("active").as_str(), "nunzio");
    sup.shutdown().await.expect("shutdown");
}

#[tokio::test]
async fn supervisor_reports_faults_and_keeps_listening() {
    let mem = memory();
    let mut p = pipeline(Arc::new(Failing));
    p.enroll("nunzio", &[voice(0.9)]).expect("enrol");
    let (sup, mut events) =
        Supervisor::start(SharedPipeline::new(p), mem, SupervisorConfig::default());
    sup.submit(frame("nuxiva", 1)).expect("submit");
    sup.submit(frame("nuxiva", 2)).expect("submit");
    for _ in 0..2 {
        assert_eq!(
            events.recv().await,
            Some(Event::Fault(BrainError::Embedding("model")))
        );
    }
    sup.shutdown().await.expect("shutdown");
}

#[tokio::test]
async fn supervisor_submit_never_blocks_and_reports_full_queue() {
    let config = SupervisorConfig {
        input_queue: 1,
        event_queue: 1,
        frame_deadline: Duration::from_secs(5),
    };
    let (sup, _events) = Supervisor::start(
        SharedPipeline::new(pipeline(Arc::new(Fixed(voice(0.9))))),
        memory(),
        config,
    );
    let mut full = 0;
    for i in 0..200 {
        if sup.submit(frame("nuxiva", i)) == Err(BrainError::QueueFull) {
            full += 1;
        }
    }
    assert!(full > 0);
    assert_eq!(
        sup.submit(Frame {
            near: vec![],
            far: vec![],
            transcript: String::new(),
            at_ms: 0
        }),
        Err(BrainError::Input("empty"))
    );
    sup.shutdown().await.expect("shutdown");
}

#[tokio::test]
async fn supervisor_stops_when_event_receiver_dropped() {
    let (sup, events) = Supervisor::start(
        SharedPipeline::new(pipeline(Arc::new(Fixed(voice(0.9))))),
        memory(),
        SupervisorConfig::default(),
    );
    drop(events);
    sup.submit(frame("nuxiva", 1)).expect("submit");
    tokio::time::sleep(Duration::from_millis(100)).await;
    assert_eq!(sup.submit(frame("nuxiva", 2)), Err(BrainError::Closed));
    sup.shutdown().await.expect("shutdown");
}

#[test]
fn config_is_sanitized() {
    let c = SupervisorConfig {
        input_queue: 0,
        event_queue: usize::MAX,
        frame_deadline: Duration::ZERO,
    }
    .sanitized();
    assert_eq!(c.input_queue, 1);
    assert_eq!(c.event_queue, 4_096);
    assert_eq!(c.frame_deadline, Duration::from_millis(10));
}
