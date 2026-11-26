use base64::Engine;
use base64::engine::general_purpose::STANDARD;

use crate::error::{StudioError, StudioResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MediaKind {
    Png,
    Jpeg,
    Webp,
    Wav,
    Mp3,
    Flac,
    Ogg,
}

impl MediaKind {
    #[must_use]
    pub const fn is_image(self) -> bool {
        matches!(self, Self::Png | Self::Jpeg | Self::Webp)
    }

    #[must_use]
    pub const fn is_audio(self) -> bool {
        !self.is_image()
    }

    #[must_use]
    pub const fn mime(self) -> &'static str {
        match self {
            Self::Png => "image/png",
            Self::Jpeg => "image/jpeg",
            Self::Webp => "image/webp",
            Self::Wav => "audio/wav",
            Self::Mp3 => "audio/mpeg",
            Self::Flac => "audio/flac",
            Self::Ogg => "audio/ogg",
        }
    }
}

#[derive(Clone, PartialEq, Eq)]
pub struct Media {
    pub kind: MediaKind,
    pub bytes: Vec<u8>,
}

impl std::fmt::Debug for Media {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Media")
            .field("kind", &self.kind)
            .field("len", &self.bytes.len())
            .finish()
    }
}

#[must_use]
pub fn sniff(bytes: &[u8]) -> Option<MediaKind> {
    let head = |n: usize| bytes.get(..n);
    if head(8) == Some(b"\x89PNG\r\n\x1a\n") {
        return Some(MediaKind::Png);
    }
    if head(3) == Some(b"\xff\xd8\xff") {
        return Some(MediaKind::Jpeg);
    }
    if head(4) == Some(b"RIFF") {
        return match bytes.get(8..12) {
            Some(b"WEBP") => Some(MediaKind::Webp),
            Some(b"WAVE") => Some(MediaKind::Wav),
            _ => None,
        };
    }
    if head(4) == Some(b"fLaC") {
        return Some(MediaKind::Flac);
    }
    if head(4) == Some(b"OggS") {
        return Some(MediaKind::Ogg);
    }
    if head(3) == Some(b"ID3") {
        return Some(MediaKind::Mp3);
    }
    match head(2) {
        Some([0xff, second]) if second & 0xe0 == 0xe0 => Some(MediaKind::Mp3),
        _ => None,
    }
}

impl Media {
    pub fn from_bytes(bytes: Vec<u8>, max: usize) -> StudioResult<Self> {
        if bytes.len() > max {
            return Err(StudioError::TooLarge);
        }
        let kind = sniff(&bytes).ok_or(StudioError::Malformed("media"))?;
        Ok(Self { kind, bytes })
    }

    pub fn from_base64(encoded: &str, max: usize) -> StudioResult<Self> {
        let estimate = encoded.len().saturating_mul(3) / 4;
        if estimate > max.saturating_add(3) {
            return Err(StudioError::TooLarge);
        }
        let bytes = STANDARD
            .decode(encoded.trim())
            .map_err(|_| StudioError::Malformed("base64"))?;
        Self::from_bytes(bytes, max)
    }
}
