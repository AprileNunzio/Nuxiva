use std::collections::{BTreeMap, BTreeSet};

use model_router::Task;
use serde::{Deserialize, Serialize};

use crate::error::{FitError, FitResult};
use crate::quant::Quant;

pub const MAX_MODELS: usize = 256;
pub const MAX_CATALOG_BYTES: usize = 256 * 1024;
const MAX_PARAMS_M: u32 = 1_000_000;
const MAX_KV_BYTES_PER_TOKEN: u32 = 4 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Model {
    pub id: String,
    pub params_m: u32,
    pub context_tokens: u32,
    pub kv_bytes_per_token: u32,
    pub quants: BTreeSet<Quant>,
    pub base_quality_bps: BTreeMap<String, u16>,
    #[serde(default)]
    pub measured_bps: BTreeMap<Quant, u16>,
}

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'-' | b'_' | b':'))
}

pub(crate) fn task_of(name: &str) -> Option<Task> {
    match name {
        "understand" => Some(Task::Understand),
        "plan" => Some(Task::Plan),
        "summarize" => Some(Task::Summarize),
        "generate" => Some(Task::Generate),
        "code" => Some(Task::Code),
        "vision" => Some(Task::Vision),
        _ => None,
    }
}

impl Model {
    pub fn validate(&self) -> FitResult<()> {
        let sizes = (1..=MAX_PARAMS_M).contains(&self.params_m)
            && self.context_tokens > 0
            && self.kv_bytes_per_token <= MAX_KV_BYTES_PER_TOKEN;
        let quality = self
            .base_quality_bps
            .iter()
            .all(|(task, q)| task_of(task).is_some() && *q <= 10_000)
            && self.measured_bps.values().all(|q| *q <= 10_000)
            && self.measured_bps.keys().all(|q| self.quants.contains(q));
        if !valid_id(&self.id) || !sizes || !quality || self.quants.is_empty() {
            return Err(FitError::Invalid("model"));
        }
        Ok(())
    }

    #[must_use]
    pub fn retention_bps(&self, quant: Quant) -> u16 {
        self.measured_bps
            .get(&quant)
            .copied()
            .unwrap_or_else(|| quant.prior_retention_bps())
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Catalog {
    models: Vec<Model>,
}

impl Catalog {
    pub fn new(models: Vec<Model>) -> FitResult<Self> {
        if models.len() > MAX_MODELS {
            return Err(FitError::Invalid("catalog_size"));
        }
        let mut seen = BTreeSet::new();
        for model in &models {
            model.validate()?;
            if !seen.insert(model.id.as_str()) {
                return Err(FitError::Invalid("duplicate"));
            }
        }
        Ok(Self { models })
    }

    pub fn from_json(bytes: &[u8]) -> FitResult<Self> {
        if bytes.len() > MAX_CATALOG_BYTES {
            return Err(FitError::Invalid("catalog_bytes"));
        }
        Self::new(serde_json::from_slice(bytes)?)
    }

    #[must_use]
    pub fn models(&self) -> &[Model] {
        &self.models
    }

    pub fn record_measurement(&mut self, id: &str, quant: Quant, bps: u16) -> FitResult<()> {
        let model = self
            .models
            .iter_mut()
            .find(|m| m.id == id)
            .ok_or(FitError::Invalid("unknown_model"))?;
        if bps > 10_000 || !model.quants.contains(&quant) {
            return Err(FitError::Invalid("measurement"));
        }
        model.measured_bps.insert(quant, bps);
        Ok(())
    }
}
