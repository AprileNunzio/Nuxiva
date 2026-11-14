use crate::barge::{Evidence, Verdict};
use crate::window::{WindowInput, judge_window};

pub const WINDOW_SAMPLES: usize = 4_000;
pub const MAX_PENDING_SAMPLES: usize = 8_000;
pub const MAX_FRAME_SAMPLES: usize = 16_000;
pub const QUARANTINE_WINDOWS: u32 = 8;
pub const MAX_SLUG_BYTES: usize = 64;

#[derive(Debug, Clone, PartialEq)]
pub struct Window {
    pub samples: Vec<f32>,
    pub voiced: bool,
}

#[derive(Debug, Default)]
pub struct WindowGate {
    audio: Vec<f32>,
    voiced_frames: u32,
    frames: u32,
    busy: bool,
}

impl WindowGate {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(&mut self, frame: &[f32], voiced: bool) -> Option<Window> {
        if frame.is_empty() || frame.len() > MAX_FRAME_SAMPLES {
            return None;
        }
        let clean = frame.iter().all(|s| s.is_finite());
        let voiced = voiced && clean;
        if clean {
            self.audio.extend_from_slice(frame);
        } else {
            self.audio
                .resize(self.audio.len().saturating_add(frame.len()), 0.0);
        }
        if self.audio.len() > MAX_PENDING_SAMPLES {
            let excess = self.audio.len().saturating_sub(MAX_PENDING_SAMPLES);
            self.audio.drain(..excess);
        }
        self.voiced_frames = self.voiced_frames.saturating_add(u32::from(voiced));
        self.frames = self.frames.saturating_add(1);
        if self.audio.len() < WINDOW_SAMPLES || self.busy {
            return None;
        }
        let start = self.audio.len().saturating_sub(WINDOW_SAMPLES);
        let samples = self.audio.split_off(start);
        let window = Window {
            samples,
            voiced: self.voiced_frames.saturating_mul(2) >= self.frames,
        };
        self.audio.clear();
        self.voiced_frames = 0;
        self.frames = 0;
        self.busy = true;
        Some(window)
    }

    pub fn release(&mut self) {
        self.busy = false;
    }

    #[must_use]
    pub const fn busy(&self) -> bool {
        self.busy
    }

    pub fn reset(&mut self) {
        self.audio.clear();
        self.voiced_frames = 0;
        self.frames = 0;
        self.busy = false;
    }
}

#[derive(Debug, Default)]
pub struct AttributionChain {
    slug: Option<String>,
    quarantine: u32,
}

impl AttributionChain {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn reset(&mut self) {
        self.slug = None;
        self.quarantine = 0;
    }

    #[must_use]
    pub const fn quarantined(&self) -> bool {
        self.quarantine > 0
    }

    fn uncertain(evidence: Evidence) -> Evidence {
        Evidence {
            verdict: Verdict::Uncertain,
            margin_permille: 0,
            ..evidence
        }
    }

    pub fn judge(&mut self, input: &WindowInput, slug: Option<&str>) -> Evidence {
        let evidence = judge_window(input);
        let held = self.quarantine > 0;
        self.quarantine = self.quarantine.saturating_sub(1);
        match evidence.verdict {
            Verdict::Broadcast => {
                self.slug = None;
                self.quarantine = QUARANTINE_WINDOWS;
                evidence
            }
            Verdict::Known => {
                let valid = slug.filter(|s| {
                    !s.is_empty()
                        && s.len() <= MAX_SLUG_BYTES
                        && s.bytes().all(|b| b.is_ascii_graphic())
                });
                match valid {
                    Some(name) if !held => {
                        if self.slug.as_deref() == Some(name) {
                            evidence
                        } else {
                            self.slug = Some(name.to_owned());
                            Self::uncertain(evidence)
                        }
                    }
                    _ => {
                        self.slug = None;
                        Self::uncertain(evidence)
                    }
                }
            }
            Verdict::Guest | Verdict::Uncertain => {
                self.slug = None;
                Self::uncertain(evidence)
            }
        }
    }
}
