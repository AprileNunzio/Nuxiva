#![forbid(unsafe_code)]

pub mod geo;
pub mod incident;
pub mod model;
pub mod net;
pub mod response;

pub use geo::{GeoError, GeoTable};
pub use model::{Action, ActionKind, Assessment, Incident, Input, Posture};

pub const MAX_INPUT: usize = 4 * 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DefenseError {
    TooLarge,
    Invalid,
    Encode,
}

impl DefenseError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::TooLarge => "defense.too_large",
            Self::Invalid => "defense.invalid",
            Self::Encode => "defense.encode",
        }
    }
}

#[must_use]
pub fn assess(input: &Input) -> Assessment {
    let incidents = incident::correlate(input);
    let actions = response::plan(input, &incidents);
    let lan = u32::try_from(
        incidents
            .iter()
            .filter(|i| i.origin == model::Origin::Lan)
            .count(),
    )
    .unwrap_or(u32::MAX);
    let total = u32::try_from(incidents.len()).unwrap_or(u32::MAX);
    Assessment {
        posture: response::posture(input.now, &incidents),
        countries: response::countries(&incidents),
        internet: total.saturating_sub(lan),
        lan,
        actions,
        incidents,
    }
}

pub fn assess_json(raw: &str) -> Result<String, DefenseError> {
    if raw.len() > MAX_INPUT {
        return Err(DefenseError::TooLarge);
    }
    let input: Input = serde_json::from_str(raw).map_err(|_| DefenseError::Invalid)?;
    if !input.now.is_finite() {
        return Err(DefenseError::Invalid);
    }
    serde_json::to_string(&assess(&input)).map_err(|_| DefenseError::Encode)
}

#[cfg(test)]
mod tests;
