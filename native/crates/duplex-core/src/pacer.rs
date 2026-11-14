use std::collections::VecDeque;

use crate::error::{DuplexError, DuplexResult};
use crate::frame::Audio;
use crate::wav::{Pcm, samples_us};

pub const MAX_FRAME_BYTES: usize = 4_096;
pub const MAX_QUEUE_FRAMES: usize = 4_096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PacerSettings {
    pub frame_ms: u32,
    pub lead_ms: u32,
}

impl Default for PacerSettings {
    fn default() -> Self {
        Self {
            frame_ms: 40,
            lead_ms: 240,
        }
    }
}

impl PacerSettings {
    pub fn validate(&self) -> DuplexResult<()> {
        if (10..=100).contains(&self.frame_ms) && (self.frame_ms..=1_000).contains(&self.lead_ms) {
            Ok(())
        } else {
            Err(DuplexError::Settings)
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ChunkInfo {
    pub rate_hz: u32,
    pub frames: u32,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Dropped {
    pub frames: u32,
    pub duration_ms: u64,
}

#[derive(Debug)]
struct Queued {
    audio: Audio,
    us: u64,
}

#[derive(Debug)]
pub struct Pacer {
    settings: PacerSettings,
    queue: VecDeque<Queued>,
    horizon_us: u64,
}

impl Pacer {
    pub fn new(settings: PacerSettings) -> DuplexResult<Self> {
        settings.validate()?;
        Ok(Self {
            settings,
            queue: VecDeque::new(),
            horizon_us: 0,
        })
    }

    pub fn push(&mut self, epoch: u32, seq: u32, pcm: &Pcm) -> DuplexResult<ChunkInfo> {
        let wanted = usize::try_from(
            u64::from(pcm.rate_hz).saturating_mul(u64::from(self.settings.frame_ms)) / 1_000,
        )
        .unwrap_or(1);
        let per_frame = wanted.clamp(1, MAX_FRAME_BYTES / 2);
        let count = pcm.samples.len().div_ceil(per_frame);
        if self.queue.len().saturating_add(count) > MAX_QUEUE_FRAMES {
            return Err(DuplexError::Capacity);
        }
        for slice in pcm.samples.chunks(per_frame) {
            let bytes: Vec<u8> = slice.iter().flat_map(|s| s.to_le_bytes()).collect();
            self.queue.push_back(Queued {
                audio: Audio {
                    epoch,
                    seq,
                    pcm: bytes,
                },
                us: samples_us(slice.len(), pcm.rate_hz),
            });
        }
        Ok(ChunkInfo {
            rate_hz: pcm.rate_hz,
            frames: u32::try_from(count).unwrap_or(u32::MAX),
            duration_ms: pcm.duration_us() / 1_000,
        })
    }

    pub fn poll(&mut self, now_ms: u64, live_epoch: u32) -> Vec<Audio> {
        let now_us = now_ms.saturating_mul(1_000);
        let ahead = u64::from(self.settings.lead_ms).saturating_mul(1_000);
        let mut out = Vec::new();
        while let Some(front) = self.queue.front() {
            if front.audio.epoch != live_epoch {
                self.queue.pop_front();
                continue;
            }
            if self.horizon_us > now_us.saturating_add(ahead) {
                break;
            }
            let Some(item) = self.queue.pop_front() else {
                break;
            };
            self.horizon_us = self.horizon_us.max(now_us).saturating_add(item.us);
            out.push(item.audio);
        }
        out
    }

    pub fn cancel(&mut self) -> Dropped {
        let frames = u32::try_from(self.queue.len()).unwrap_or(u32::MAX);
        let us: u64 = self.queue.iter().map(|q| q.us).sum();
        self.queue.clear();
        self.horizon_us = 0;
        Dropped {
            frames,
            duration_ms: us / 1_000,
        }
    }

    #[must_use]
    pub fn queued_frames(&self) -> usize {
        self.queue.len()
    }

    #[must_use]
    pub fn in_flight_ms(&self, now_ms: u64) -> u64 {
        self.horizon_us.saturating_sub(now_ms.saturating_mul(1_000)) / 1_000
    }
}
