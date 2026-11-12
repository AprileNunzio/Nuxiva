use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ZLayer {
    Z0Ambient = 0,
    Z1PrimaryStage = 1,
    Z2ContextualHud = 2,
    Z3Assistant = 3,
    Z4CriticalInterrupt = 4,
}

impl ZLayer {
    #[must_use]
    pub const fn layer_code(&self) -> &'static str {
        match self {
            Self::Z0Ambient => "Z0",
            Self::Z1PrimaryStage => "Z1",
            Self::Z2ContextualHud => "Z2",
            Self::Z3Assistant => "Z3",
            Self::Z4CriticalInterrupt => "Z4",
        }
    }

    #[must_use]
    pub const fn z_index(&self) -> u32 {
        match self {
            Self::Z0Ambient => 0,
            Self::Z1PrimaryStage => 10,
            Self::Z2ContextualHud => 20,
            Self::Z3Assistant => 30,
            Self::Z4CriticalInterrupt => 100,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZLayerState {
    pub layer: ZLayer,
    pub is_active: bool,
    pub state_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ZLayerStack {
    pub z0_ambient: ZLayerState,
    pub z1_stage: ZLayerState,
    pub z2_hud: ZLayerState,
    pub z3_assistant: ZLayerState,
    pub z4_critical: ZLayerState,
}

impl Default for ZLayerStack {
    fn default() -> Self {
        Self {
            z0_ambient: ZLayerState {
                layer: ZLayer::Z0Ambient,
                is_active: true,
                state_key: "active".to_string(),
            },
            z1_stage: ZLayerState {
                layer: ZLayer::Z1PrimaryStage,
                is_active: false,
                state_key: "idle".to_string(),
            },
            z2_hud: ZLayerState {
                layer: ZLayer::Z2ContextualHud,
                is_active: false,
                state_key: "none".to_string(),
            },
            z3_assistant: ZLayerState {
                layer: ZLayer::Z3Assistant,
                is_active: true,
                state_key: "core_hero".to_string(),
            },
            z4_critical: ZLayerState {
                layer: ZLayer::Z4CriticalInterrupt,
                is_active: false,
                state_key: "standby".to_string(),
            },
        }
    }
}
