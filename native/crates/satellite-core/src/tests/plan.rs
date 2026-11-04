use super::{Fixture, base, microphone_and_speaker};
use crate::backends::{Task, builtin};
use crate::plan::{Placement, plan};
use crate::probe::profile;

#[test]
fn weak_cpu_sends_transcription_to_the_server_but_keeps_wake_word() -> Result<(), String> {
    let fx = Fixture::new("weak")?;
    base(&fx, 2, 1024 * 1024)?;
    microphone_and_speaker(&fx)?;
    let steps = plan(&profile(&fx.root(), &builtin(), &[]));
    let get = |task| {
        steps
            .steps
            .iter()
            .find(|s| s.task == task)
            .map(|s| s.placement.clone())
    };
    assert_eq!(
        get(Task::WakeWord),
        Some(Placement::Edge {
            backend: "cpu".into()
        })
    );
    assert_eq!(
        get(Task::Vad),
        Some(Placement::Edge {
            backend: "cpu".into()
        })
    );
    assert_eq!(get(Task::Stt), Some(Placement::Server));
    assert_eq!(
        get(Task::Tts),
        Some(Placement::Edge {
            backend: "cpu".into()
        })
    );
    Ok(())
}

#[test]
fn plan_serialises_to_a_compact_shape() -> Result<(), String> {
    let fx = Fixture::new("shape")?;
    base(&fx, 4, 4 * 1024 * 1024)?;
    let steps = plan(&profile(&fx.root(), &builtin(), &[]));
    let text = serde_json::to_string(&steps).map_err(|e| e.to_string())?;
    assert!(
        text.contains(r#"{"task":"wake_word","target":"unavailable","reason":"no_microphone"}"#),
        "{text}"
    );
    assert!(
        text.contains(r#"{"task":"llm","target":"server"}"#),
        "{text}"
    );
    Ok(())
}
