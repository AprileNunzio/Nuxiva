mod event;
pub(crate) mod ident;
mod percept;
mod plan;
mod result;
mod task;

use serde::Serialize;
use serde::de::DeserializeOwned;

use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;

pub use event::{Phase, StepEvent};
pub use ident::{Digest, Ident};
pub use percept::{Affect, Channel, Percept};
pub use plan::{Edge, Plan, Step, StepBudget, VerifySpec};
pub use result::{Outcome, Usage, WorkerError, WorkerErrorKind, WorkerResult};
pub use task::{Constraints, Level, TaskEnvelope};

pub const SCHEMA_VERSION: u32 = 1;

pub trait Validate {
    fn validate(&self, settings: &Settings) -> SwarmResult<()>;
}

pub(crate) fn version(found: u32) -> SwarmResult<()> {
    if found == SCHEMA_VERSION {
        Ok(())
    } else {
        Err(SwarmError::Version)
    }
}

pub fn decode<T: DeserializeOwned + Validate>(raw: &[u8], settings: &Settings) -> SwarmResult<T> {
    if raw.len() > settings.max_payload_bytes {
        return Err(SwarmError::TooLarge);
    }
    let value: T = serde_json::from_slice(raw).map_err(|_| SwarmError::Parse)?;
    value.validate(settings)?;
    Ok(value)
}

pub fn encode<T: Serialize + Validate>(value: &T, settings: &Settings) -> SwarmResult<Vec<u8>> {
    value.validate(settings)?;
    let bytes = serde_json::to_vec(value).map_err(|_| SwarmError::Serialize)?;
    if bytes.len() > settings.max_payload_bytes {
        return Err(SwarmError::TooLarge);
    }
    Ok(bytes)
}
