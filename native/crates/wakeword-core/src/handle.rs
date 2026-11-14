use std::collections::HashMap;
use std::sync::{Mutex, MutexGuard, OnceLock};

use crate::error::{WakeError, WakeResult};
use crate::model::Model;
use crate::stream::{Config, Detection, Detector};

pub const MAX_HANDLES: usize = 8;
pub const MAX_PUSH_BYTES: usize = 16_000 * 2 * 10;
pub const MAX_MODEL_BYTES: usize = 2 * 1024 * 1024;

#[derive(Debug, Default)]
struct Registry {
    next: u64,
    items: HashMap<u64, Detector>,
}

fn registry() -> MutexGuard<'static, Registry> {
    static CELL: OnceLock<Mutex<Registry>> = OnceLock::new();
    CELL.get_or_init(|| Mutex::new(Registry::default()))
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

pub fn create(model: &[u8], sensitivity: f32) -> WakeResult<u64> {
    if model.len() > MAX_MODEL_BYTES {
        return Err(WakeError::Model);
    }
    let model = Model::from_bytes(model)?;
    let detector = Detector::new(
        model,
        Config {
            sensitivity,
            ..Config::default()
        },
    )?;
    let mut reg = registry();
    if reg.items.len() >= MAX_HANDLES {
        return Err(WakeError::Config);
    }
    reg.next = reg.next.saturating_add(1);
    let id = reg.next;
    reg.items.insert(id, detector);
    Ok(id)
}

pub fn push(handle: u64, pcm: &[u8]) -> WakeResult<Vec<Detection>> {
    if pcm.len() > MAX_PUSH_BYTES || pcm.len() % 2 != 0 {
        return Err(WakeError::Config);
    }
    let samples: Vec<i16> = pcm
        .chunks_exact(2)
        .map(|c| {
            i16::from_le_bytes([
                c.first().copied().unwrap_or(0),
                c.get(1).copied().unwrap_or(0),
            ])
        })
        .collect();
    let mut reg = registry();
    let detector = reg.items.get_mut(&handle).ok_or(WakeError::Config)?;
    Ok(detector.push(&samples))
}

pub fn destroy(handle: u64) {
    registry().items.remove(&handle);
}

#[must_use]
pub fn encode(detection: &Detection) -> Vec<u8> {
    let mut out = Vec::with_capacity(4_usize.saturating_add(detection.pcm.len().saturating_mul(2)));
    out.extend_from_slice(&detection.confidence.to_le_bytes());
    out.extend(detection.pcm.iter().flat_map(|s| s.to_le_bytes()));
    out
}
