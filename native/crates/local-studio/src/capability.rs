use serde_json::Value;

use crate::error::{StudioError, StudioResult};

pub const MAX_SCHEMA_BYTES: usize = 4 << 20;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Capability {
    Chat,
    Image,
    Speech,
    Embeddings,
}

impl Capability {
    pub const ALL: [Self; 4] = [Self::Chat, Self::Image, Self::Speech, Self::Embeddings];

    #[must_use]
    pub const fn path(self) -> &'static str {
        match self {
            Self::Chat => "v1/chat/completions",
            Self::Image => "v1/images/generations",
            Self::Speech => "v1/audio/speech",
            Self::Embeddings => "v1/embeddings",
        }
    }

    #[must_use]
    pub const fn key(self) -> &'static str {
        match self {
            Self::Chat => "chat",
            Self::Image => "image",
            Self::Speech => "speech",
            Self::Embeddings => "embeddings",
        }
    }

    const fn bit(self) -> u8 {
        match self {
            Self::Chat => 1,
            Self::Image => 2,
            Self::Speech => 4,
            Self::Embeddings => 8,
        }
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Capabilities(u8);

impl Capabilities {
    #[must_use]
    pub const fn none() -> Self {
        Self(0)
    }

    #[must_use]
    pub const fn with(self, capability: Capability) -> Self {
        Self(self.0 | capability.bit())
    }

    #[must_use]
    pub const fn has(self, capability: Capability) -> bool {
        self.0 & capability.bit() != 0
    }

    pub fn require(self, capability: Capability) -> StudioResult<()> {
        if self.has(capability) {
            Ok(())
        } else {
            Err(StudioError::Unsupported(capability.key()))
        }
    }

    pub fn from_openapi(schema: &str) -> StudioResult<Self> {
        if schema.len() > MAX_SCHEMA_BYTES {
            return Err(StudioError::TooLarge);
        }
        let parsed: Value = serde_json::from_str(schema)?;
        let paths = parsed
            .get("paths")
            .and_then(Value::as_object)
            .ok_or(StudioError::Malformed("openapi"))?;
        let found = Capability::ALL
            .iter()
            .fold(Self::none(), |acc, capability| {
                let wanted = format!("/{}", capability.path());
                let declared = paths
                    .get(&wanted)
                    .and_then(Value::as_object)
                    .is_some_and(|ops| ops.contains_key("post"));
                if declared { acc.with(*capability) } else { acc }
            });
        Ok(found)
    }

    #[must_use]
    pub fn keys(self) -> Vec<&'static str> {
        Capability::ALL
            .iter()
            .filter(|c| self.has(**c))
            .map(|c| c.key())
            .collect()
    }
}
