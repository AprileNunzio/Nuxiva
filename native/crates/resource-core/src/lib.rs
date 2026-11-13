#![forbid(unsafe_code)]

pub mod level;
pub mod model;
pub mod plan;

pub use model::{Action, ActionKind, Class, Component, Input, Kind, Level, Plan, System};
pub use plan::plan;

pub const MAX_INPUT: usize = 1024 * 1024;
pub const MAX_COMPONENTS: usize = 512;
pub const MAX_ID: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResourceError {
    TooLarge,
    Invalid,
    Encode,
}

impl ResourceError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::TooLarge => "resource.too_large",
            Self::Invalid => "resource.invalid",
            Self::Encode => "resource.encode",
        }
    }
}

fn id_ok(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= MAX_ID
        && id.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'-' | b'.' | b':')
        })
}

fn valid(input: &Input) -> bool {
    let system = &input.system;
    system.mem_total > 0
        && system.cpu_percent.is_finite()
        && system.gpu_percent.is_finite()
        && input.components.len() <= MAX_COMPONENTS
        && input
            .components
            .iter()
            .all(|c| id_ok(&c.id) && c.cpu_percent.is_finite())
}

pub fn plan_json(raw: &str) -> Result<String, ResourceError> {
    if raw.len() > MAX_INPUT {
        return Err(ResourceError::TooLarge);
    }
    let input: Input = serde_json::from_str(raw).map_err(|_| ResourceError::Invalid)?;
    if !valid(&input) {
        return Err(ResourceError::Invalid);
    }
    serde_json::to_string(&plan(&input)).map_err(|_| ResourceError::Encode)
}

#[cfg(test)]
mod tests;
