use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Quant {
    F16,
    Q8,
    Q6,
    Q5,
    Q4,
    Q3,
    Q2,
}

impl Quant {
    pub const ALL: [Self; 7] = [
        Self::F16,
        Self::Q8,
        Self::Q6,
        Self::Q5,
        Self::Q4,
        Self::Q3,
        Self::Q2,
    ];

    #[must_use]
    pub const fn deci_bits(self) -> u64 {
        match self {
            Self::F16 => 160,
            Self::Q8 => 85,
            Self::Q6 => 66,
            Self::Q5 => 57,
            Self::Q4 => 48,
            Self::Q3 => 39,
            Self::Q2 => 26,
        }
    }

    #[must_use]
    pub const fn prior_retention_bps(self) -> u16 {
        match self {
            Self::F16 => 10_000,
            Self::Q8 => 9_950,
            Self::Q6 => 9_900,
            Self::Q5 => 9_800,
            Self::Q4 => 9_600,
            Self::Q3 => 9_000,
            Self::Q2 => 7_800,
        }
    }
}
