use std::collections::BTreeMap;

use model_router::{Placement, Profile, Task};
use serde::Serialize;

use crate::catalog::{Catalog, Model, task_of};
use crate::error::{FitError, FitResult};
use crate::node::{Device, Node};
use crate::quant::Quant;

const MIB: u64 = 1_048_576;
const RUNTIME_MB: u64 = 256;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Need {
    pub task: Task,
    pub context_tokens: u32,
    pub min_quality_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Fit {
    pub id: String,
    pub model: String,
    pub quant: Quant,
    pub device: Device,
    pub memory_mb: u64,
    pub expected_bps: u16,
}

#[must_use]
pub fn memory_mb(model: &Model, quant: Quant, context_tokens: u32) -> u64 {
    let weights = u64::from(model.params_m)
        .saturating_mul(1_000_000)
        .saturating_mul(quant.deci_bits())
        / 80
        / MIB;
    let kv = u64::from(model.kv_bytes_per_token).saturating_mul(u64::from(context_tokens)) / MIB;
    weights
        .saturating_add(weights / 10)
        .saturating_add(kv)
        .saturating_add(RUNTIME_MB)
}

fn scaled(base: u16, retention: u16) -> u16 {
    let value = u32::from(base).saturating_mul(u32::from(retention)) / 10_000;
    u16::try_from(value).unwrap_or(10_000)
}

fn quant_name(quant: Quant) -> &'static str {
    match quant {
        Quant::F16 => "f16",
        Quant::Q8 => "q8",
        Quant::Q6 => "q6",
        Quant::Q5 => "q5",
        Quant::Q4 => "q4",
        Quant::Q3 => "q3",
        Quant::Q2 => "q2",
    }
}

fn task_name(task: Task) -> &'static str {
    match task {
        Task::Understand => "understand",
        Task::Plan => "plan",
        Task::Summarize => "summarize",
        Task::Generate => "generate",
        Task::Code => "code",
        Task::Vision => "vision",
    }
}

fn candidates<'a>(
    node: &'a Node,
    model: &'a Model,
    need: &'a Need,
) -> impl Iterator<Item = Fit> + 'a {
    let base = model
        .base_quality_bps
        .get(task_name(need.task))
        .copied()
        .unwrap_or(0);
    let usable =
        model.params_m <= node.max_params_m() && model.context_tokens >= need.context_tokens;
    model
        .quants
        .iter()
        .filter(move |_| usable)
        .flat_map(move |quant| [Device::Gpu, Device::Cpu].map(|device| (*quant, device)))
        .filter_map(move |(quant, device)| {
            let memory = memory_mb(model, quant, need.context_tokens);
            let expected = scaled(base, model.retention_bps(quant));
            (memory <= node.usable_mb(device) && expected >= need.min_quality_bps).then(|| Fit {
                id: format!("{}:{}", model.id, quant_name(quant)),
                model: model.id.clone(),
                quant,
                device,
                memory_mb: memory,
                expected_bps: expected,
            })
        })
}

pub fn plan(node: &Node, catalog: &Catalog, need: &Need) -> FitResult<Fit> {
    node.validate()?;
    let mut fits: Vec<Fit> = catalog
        .models()
        .iter()
        .flat_map(|model| candidates(node, model, need))
        .collect();
    fits.sort_by(|a, b| {
        b.expected_bps
            .cmp(&a.expected_bps)
            .then(a.device.cmp(&b.device))
            .then(a.memory_mb.cmp(&b.memory_mb))
            .then(a.id.cmp(&b.id))
    });
    fits.into_iter().next().ok_or(FitError::NoFit)
}

pub fn profile(fit: &Fit, catalog: &Catalog, latency_ms: u32) -> FitResult<Profile> {
    let model = catalog
        .models()
        .iter()
        .find(|m| m.id == fit.model)
        .ok_or(FitError::Invalid("unknown_model"))?;
    let retention = model.retention_bps(fit.quant);
    let quality_bps: BTreeMap<Task, u16> = model
        .base_quality_bps
        .iter()
        .filter_map(|(name, base)| Some((task_of(name)?, scaled(*base, retention))))
        .collect();
    let profile = Profile {
        id: fit.id.clone(),
        placement: Placement::Local,
        context_tokens: model.context_tokens,
        micro_per_1k_in: 0,
        micro_per_1k_out: 0,
        latency_ms,
        quality_bps,
    };
    profile
        .validate()
        .map_err(|_| FitError::Invalid("profile"))?;
    Ok(profile)
}
