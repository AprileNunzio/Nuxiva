use serde::{Deserialize, Serialize};

use crate::error::{DuplexError, DuplexResult};
use crate::settings::{PROTOCOL_VERSION, Settings};
use crate::state::State;

pub const AUDIO_KIND: u8 = 1;
pub const AUDIO_HEADER: usize = 9;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum Control {
    Hello {
        version: u32,
    },
    State {
        state: State,
        #[serde(rename = "gen")]
        epoch: u32,
    },
    Text {
        #[serde(rename = "gen")]
        epoch: u32,
        seq: u32,
        text: String,
    },
    Chunk {
        #[serde(rename = "gen")]
        epoch: u32,
        seq: u32,
        rate_hz: u32,
        frames: u32,
    },
    Cut {
        #[serde(rename = "gen")]
        epoch: u32,
    },
    Spoken {
        #[serde(rename = "gen")]
        epoch: u32,
        chars: u32,
    },
    Error {
        code: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Audio {
    pub epoch: u32,
    pub seq: u32,
    pub pcm: Vec<u8>,
}

impl Control {
    pub fn parse(text: &str, settings: &Settings) -> DuplexResult<Self> {
        let limit = settings.max_text_bytes.saturating_add(256);
        if text.len() > limit {
            return Err(DuplexError::TooLarge);
        }
        let frame: Self = serde_json::from_str(text).map_err(|_| DuplexError::Parse)?;
        match &frame {
            Self::Hello { version } if *version != PROTOCOL_VERSION => Err(DuplexError::Version),
            Self::Text { text, .. } if text.len() > settings.max_text_bytes => {
                Err(DuplexError::TooLarge)
            }
            Self::Error { code } if code.len() > 64 => Err(DuplexError::TooLarge),
            _ => Ok(frame),
        }
    }

    pub fn encode(&self) -> DuplexResult<String> {
        serde_json::to_string(self).map_err(|_| DuplexError::Serialize)
    }
}

impl Audio {
    pub fn decode(bytes: &[u8], settings: &Settings) -> DuplexResult<Self> {
        let (header, pcm) = bytes
            .split_at_checked(AUDIO_HEADER)
            .ok_or(DuplexError::Parse)?;
        let (kind, rest) = header.split_first().ok_or(DuplexError::Parse)?;
        if *kind != AUDIO_KIND {
            return Err(DuplexError::Invalid);
        }
        if pcm.is_empty() || pcm.len() > settings.max_audio_bytes {
            return Err(DuplexError::TooLarge);
        }
        let (epoch, seq) = rest.split_at_checked(4).ok_or(DuplexError::Parse)?;
        Ok(Self {
            epoch: u32::from_be_bytes(epoch.try_into().map_err(|_| DuplexError::Parse)?),
            seq: u32::from_be_bytes(seq.try_into().map_err(|_| DuplexError::Parse)?),
            pcm: pcm.to_vec(),
        })
    }

    #[must_use]
    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(AUDIO_HEADER.saturating_add(self.pcm.len()));
        out.push(AUDIO_KIND);
        out.extend_from_slice(&self.epoch.to_be_bytes());
        out.extend_from_slice(&self.seq.to_be_bytes());
        out.extend_from_slice(&self.pcm);
        out
    }
}
