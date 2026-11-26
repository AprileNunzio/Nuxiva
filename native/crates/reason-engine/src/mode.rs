use serde::{Deserialize, Serialize};

use crate::error::{EngineError, EngineResult};
use crate::ledger::GateStatus;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Off,
    #[default]
    Shadow,
    Active,
}

impl Mode {
    pub fn parse(raw: &str) -> EngineResult<Self> {
        match raw {
            "off" => Ok(Self::Off),
            "shadow" => Ok(Self::Shadow),
            "active" => Ok(Self::Active),
            _ => Err(EngineError::Mode("unknown")),
        }
    }

    #[must_use]
    pub fn key(self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::Shadow => "shadow",
            Self::Active => "active",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Switch {
    pub mode: Mode,
    pub forced: bool,
}

impl Switch {
    pub fn set(&mut self, target: Mode, status: &GateStatus, force: bool) -> EngineResult<Mode> {
        if target == Mode::Active && !status.ready && !force {
            return Err(EngineError::Mode("gate_closed"));
        }
        self.mode = target;
        self.forced = target == Mode::Active && !status.ready;
        Ok(self.mode)
    }

    pub fn kill(&mut self) {
        self.mode = Mode::Off;
        self.forced = false;
    }

    #[must_use]
    pub fn observes(&self) -> bool {
        self.mode != Mode::Off
    }

    #[must_use]
    pub fn acts(&self) -> bool {
        self.mode == Mode::Active
    }
}
