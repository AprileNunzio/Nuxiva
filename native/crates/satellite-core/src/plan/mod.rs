use serde::Serialize;

use crate::backends::{Accelerator, Kind, Task};
use crate::probe::Profile;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "target", rename_all = "snake_case")]
pub enum Placement {
    Edge { backend: String },
    Server,
    Unavailable { reason: &'static str },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Step {
    pub task: Task,
    #[serde(flatten)]
    pub placement: Placement,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Missing {
    pub backend: String,
    pub vendor: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Plan {
    pub steps: Vec<Step>,
    pub missing_runtimes: Vec<Missing>,
}

const CPU_STT_MIN_RAM_MB: u32 = 1536;
const CPU_STT_MIN_CORES: u32 = 4;
const CPU_TTS_MIN_RAM_MB: u32 = 512;
const CPU_VISION_MIN_RAM_MB: u32 = 2048;
const CPU_VISION_MIN_CORES: u32 = 4;

#[must_use]
pub fn plan(profile: &Profile) -> Plan {
    let steps = Task::ALL
        .iter()
        .map(|task| Step {
            task: *task,
            placement: place(profile, *task),
        })
        .collect();
    let missing_runtimes = profile
        .accelerators
        .iter()
        .filter(|acc| !acc.ready && acc.kind != Kind::Cpu)
        .map(|acc| Missing {
            backend: acc.id.clone(),
            vendor: acc.vendor.clone(),
        })
        .collect();
    Plan {
        steps,
        missing_runtimes,
    }
}

fn place(profile: &Profile, task: Task) -> Placement {
    if let Some(reason) = missing_sense(profile, task) {
        return Placement::Unavailable { reason };
    }
    profile
        .accelerators
        .iter()
        .filter(|acc| acc.ready && acc.tasks.contains(&task))
        .find(|acc| fits(profile, acc, task))
        .map_or(Placement::Server, |acc| Placement::Edge {
            backend: acc.id.clone(),
        })
}

fn missing_sense(profile: &Profile, task: Task) -> Option<&'static str> {
    let senses = &profile.senses;
    match task {
        Task::WakeWord | Task::Vad | Task::Stt if senses.microphones.is_empty() => {
            Some("no_microphone")
        }
        Task::Tts if senses.speakers.is_empty() => Some("no_speaker"),
        Task::Vision if senses.cameras.is_empty() => Some("no_camera"),
        _ => None,
    }
}

fn fits(profile: &Profile, acc: &Accelerator, task: Task) -> bool {
    let ram = profile.system.ram_mb;
    let cores = profile.system.cores;
    if task == Task::Llm {
        return ram >= acc.llm_min_ram_mb;
    }
    if acc.kind != Kind::Cpu {
        return true;
    }
    match task {
        Task::WakeWord | Task::Vad => true,
        Task::Tts => ram >= CPU_TTS_MIN_RAM_MB,
        Task::Stt => ram >= CPU_STT_MIN_RAM_MB && cores >= CPU_STT_MIN_CORES,
        Task::Vision => ram >= CPU_VISION_MIN_RAM_MB && cores >= CPU_VISION_MIN_CORES,
        Task::Llm => false,
    }
}
