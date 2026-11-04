use serde_json::{Map, Value, json};

use crate::backends::{Accelerator, Kind};
use crate::plan::{Placement, Plan};
use crate::probe::Profile;
use crate::probe::system::Metrics;

pub const AGENT: &str = "rust";

#[must_use]
pub fn heartbeat(profile: &Profile, plan: &Plan, metrics: &Metrics, adapted: bool) -> Value {
    json!({
        "version": env!("CARGO_PKG_VERSION"),
        "agent": AGENT,
        "hostname": profile.system.hostname,
        "metrics": metrics,
        "capabilities": capabilities(profile, plan),
        "hardware": hardware(profile),
        "offload": offload(plan),
        "adapted": adapted,
    })
}

#[must_use]
pub fn capabilities(profile: &Profile, plan: &Plan) -> Vec<String> {
    let senses = &profile.senses;
    let mut caps: Vec<String> = [
        (!senses.microphones.is_empty(), "audio"),
        (!senses.speakers.is_empty(), "speaker"),
        (!senses.cameras.is_empty(), "camera"),
        (senses.ir_camera, "ir_camera"),
        (senses.bluetooth, "bluetooth"),
        (senses.gpio_chips > 0, "gpio"),
        (senses.i2c_buses > 0, "i2c"),
    ]
    .into_iter()
    .filter(|&(present, _name)| present)
    .map(|(_present, name)| name.to_owned())
    .collect();
    caps.extend(
        profile
            .accelerators
            .iter()
            .filter(|acc| acc.ready && acc.kind != Kind::Cpu)
            .map(|acc| kind_name(acc.kind).to_owned()),
    );
    caps.extend(plan.steps.iter().filter_map(|step| match step.placement {
        Placement::Edge { .. } => Some(format!("edge_{}", task_name(step.task))),
        _ => None,
    }));
    caps.sort();
    caps.dedup();
    caps.truncate(12);
    caps
}

fn hardware(profile: &Profile) -> Value {
    let system = &profile.system;
    let senses = &profile.senses;
    json!({
        "cores": system.cores,
        "ram_gb": f64::from(system.ram_mb) / 1024.0,
        "disk_gb": system.disk_gb,
        "avx2": system.cpu_features.iter().any(|f| f == "avx2"),
        "arch": system.arch,
        "os": system.os,
        "gpu": gpu(&profile.accelerators),
        "cameras": senses.cameras,
        "ir_camera": senses.ir_camera,
        "audio_in": senses.microphones,
        "audio_out": senses.speakers,
        "bluetooth": senses.bluetooth,
        "usb": senses.usb,
        "soc": {"vendor": profile.soc.vendor, "family": profile.soc.family, "model": system.model},
        "cpu_features": system.cpu_features,
        "accelerators": profile.accelerators.iter().filter(|a| a.kind != Kind::Cpu).map(accelerator).collect::<Vec<_>>(),
    })
}

fn accelerator(acc: &Accelerator) -> Value {
    json!({
        "id": acc.id,
        "vendor": acc.vendor,
        "kind": kind_name(acc.kind),
        "ready": acc.ready,
        "runtime": acc.runtime.clone().unwrap_or_default(),
        "tasks": acc.tasks.iter().map(|t| task_name(*t)).collect::<Vec<_>>(),
    })
}

fn gpu(accelerators: &[Accelerator]) -> String {
    accelerators
        .iter()
        .find(|acc| acc.kind == Kind::Gpu)
        .map(|acc| format!("{} ({})", acc.vendor, acc.id))
        .unwrap_or_default()
}

fn offload(plan: &Plan) -> Value {
    let mut map = Map::new();
    for step in &plan.steps {
        let value = match &step.placement {
            Placement::Edge { backend } => json!({"target": "edge", "backend": backend}),
            Placement::Server => json!({"target": "server"}),
            Placement::Unavailable { reason } => json!({"target": "unavailable", "reason": reason}),
        };
        map.insert(task_name(step.task).to_owned(), value);
    }
    Value::Object(map)
}

#[must_use]
pub fn kind_name(kind: Kind) -> &'static str {
    match kind {
        Kind::Npu => "npu",
        Kind::Gpu => "gpu",
        Kind::Tpu => "tpu",
        Kind::Dsp => "dsp",
        Kind::Cpu => "cpu",
    }
}

#[must_use]
pub fn task_name(task: crate::backends::Task) -> &'static str {
    use crate::backends::Task;
    match task {
        Task::WakeWord => "wake_word",
        Task::Vad => "vad",
        Task::Stt => "stt",
        Task::Tts => "tts",
        Task::Vision => "vision",
        Task::Llm => "llm",
    }
}
