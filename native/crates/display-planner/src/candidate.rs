use crate::category::Category;
use crate::grid::Slot;
use nuxiva_display_domain::Sensitivity;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Size {
    S,
    #[default]
    M,
    L,
    Xl,
    Full,
}

impl Size {
    #[must_use]
    pub const fn cells(self) -> (u8, u8) {
        match self {
            Self::S => (3, 2),
            Self::M => (4, 3),
            Self::L => (6, 4),
            Self::Xl => (8, 5),
            Self::Full => (12, 24),
        }
    }
}

#[allow(clippy::struct_excessive_bools)]
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Candidate {
    pub key: String,
    pub widget: String,
    #[serde(default)]
    pub category: Option<Category>,
    #[serde(default)]
    pub importance: u8,
    #[serde(default)]
    pub urgency: u8,
    #[serde(default = "public")]
    pub sensitivity: Sensitivity,
    #[serde(default)]
    pub owner: Option<String>,
    #[serde(default)]
    pub size: Size,
    #[serde(default = "unit")]
    pub cost: f32,
    #[serde(default)]
    pub exclusive: Option<String>,
    #[serde(default)]
    pub media: Option<String>,
    #[serde(default)]
    pub source: Option<String>,
    #[serde(default)]
    pub forced: bool,
    #[serde(default)]
    pub intent: bool,
    #[serde(default)]
    pub pinned: Option<Slot>,
    #[serde(default)]
    pub needs_webgl2: bool,
    #[serde(default)]
    pub quarantined: bool,
    #[serde(default)]
    pub guest_safe: bool,
    #[serde(default)]
    pub relevance: f32,
    #[serde(default)]
    pub preference: f32,
    #[serde(default)]
    pub age_ms: u64,
    #[serde(default)]
    pub ttl_ms: Option<u64>,
    #[serde(default)]
    pub interacted_ms: Option<u64>,
}

const fn public() -> Sensitivity {
    Sensitivity::Public
}

const fn unit() -> f32 {
    1.0
}

impl Candidate {
    #[must_use]
    pub fn category(&self) -> Category {
        self.category
            .unwrap_or_else(|| crate::category::category_of(&self.widget))
    }

    #[must_use]
    pub fn must_show(&self) -> bool {
        self.forced
            || self.intent
            || self.pinned.is_some()
            || self.category() == Category::Safety
            || self.urgency >= 3
    }
}
