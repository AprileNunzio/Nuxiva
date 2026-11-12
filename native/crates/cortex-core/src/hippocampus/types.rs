use serde::{Deserialize, Serialize};

use crate::platform::error::{CortexError, CortexResult};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Thresholds {
    pub fast_similarity: f32,
    pub grey_similarity: f32,
    pub inhibition_limit: f32,
    pub fast_weight: f32,
    pub grey_weight: f32,
}

impl Default for Thresholds {
    fn default() -> Self {
        Self {
            fast_similarity: 0.85,
            grey_similarity: 0.70,
            inhibition_limit: 0.60,
            fast_weight: 0.75,
            grey_weight: 0.50,
        }
    }
}

fn unit_interval(value: f32) -> bool {
    value.is_finite() && (0.0..=1.0).contains(&value)
}

impl Thresholds {
    pub fn validate(&self) -> CortexResult<()> {
        let bounded = [
            self.fast_similarity,
            self.grey_similarity,
            self.inhibition_limit,
            self.fast_weight,
            self.grey_weight,
        ]
        .into_iter()
        .all(unit_interval);
        let ordered =
            self.grey_similarity <= self.fast_similarity && self.grey_weight <= self.fast_weight;
        if bounded && ordered {
            Ok(())
        } else {
            Err(CortexError::InvalidThresholds)
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    FastPath,
    GreyZone,
    SlowPath,
}

impl Verdict {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::FastPath => "fast_path",
            Self::GreyZone => "grey_zone",
            Self::SlowPath => "slow_path",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SlowReason {
    NoNeurons,
    LowSimilarity,
    Inhibited,
    LowWeight,
}

impl SlowReason {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NoNeurons => "no_neurons",
            Self::LowSimilarity => "low_similarity",
            Self::Inhibited => "inhibited",
            Self::LowWeight => "low_weight",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Decision {
    pub verdict: Verdict,
    pub reason: Option<SlowReason>,
    pub neuron_id: Option<String>,
    pub positive_similarity: f32,
    pub negative_similarity: f32,
    pub synaptic_weight: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Neuron {
    pub id: String,
    pub weight: f32,
    pub dendrites: Vec<Vec<f32>>,
    pub inhibitions: Vec<Vec<f32>>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Candidate<'a> {
    pub neuron: &'a Neuron,
    pub positive_similarity: f32,
    pub negative_similarity: f32,
}

#[cfg(test)]
mod tests {
    use super::{CortexError, Thresholds};

    #[test]
    fn default_thresholds_are_valid() {
        assert_eq!(Thresholds::default().validate(), Ok(()));
    }

    #[test]
    fn inverted_or_out_of_range_thresholds_are_rejected() {
        let inverted = Thresholds {
            grey_similarity: 0.9,
            ..Thresholds::default()
        };
        let out_of_range = Thresholds {
            fast_weight: 1.5,
            ..Thresholds::default()
        };
        let not_finite = Thresholds {
            inhibition_limit: f32::NAN,
            ..Thresholds::default()
        };
        for broken in [inverted, out_of_range, not_finite] {
            assert_eq!(broken.validate(), Err(CortexError::InvalidThresholds));
        }
    }
}
