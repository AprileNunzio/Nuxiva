use std::sync::{Arc, Mutex, PoisonError};

use nuxiva_ear_core::aec::{EchoCanceller, MAX_BLOCK};
use nuxiva_ear_core::{VoiceBook, VoicePolicy};

use crate::error::{BrainError, BrainResult};
use crate::gate::{GateVerdict, Gatekeeper};

const MAX_TRANSCRIPT_BYTES: usize = 16 * 1024;

pub trait Embedder: Send + Sync {
    fn embed(&self, pcm: &[f32]) -> BrainResult<Vec<f32>>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Layer {
    Aec,
    Biometry,
    Gatekeeper,
}

#[derive(Debug, Clone)]
pub struct Frame {
    pub near: Vec<f32>,
    pub far: Vec<f32>,
    pub transcript: String,
    pub at_ms: u64,
}

impl Frame {
    pub fn validate(&self) -> BrainResult<()> {
        if self.near.is_empty() {
            return Err(BrainError::Input("empty"));
        }
        if self.near.len() != self.far.len() {
            return Err(BrainError::Input("length"));
        }
        if self.near.len() > MAX_BLOCK {
            return Err(BrainError::Input("block"));
        }
        if self.transcript.len() > MAX_TRANSCRIPT_BYTES {
            return Err(BrainError::Input("transcript"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Decision {
    Accepted {
        speaker: Option<String>,
        text: String,
        score: f32,
        at_ms: u64,
    },
    Rejected {
        layer: Layer,
        reason: &'static str,
    },
}

pub struct SensoryPipeline {
    aec: EchoCanceller,
    book: VoiceBook,
    embedder: Arc<dyn Embedder>,
    gate: Gatekeeper,
    last_accepted_ms: Option<u64>,
}

impl std::fmt::Debug for SensoryPipeline {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SensoryPipeline(..)")
    }
}

impl SensoryPipeline {
    #[must_use]
    pub fn new(embedder: Arc<dyn Embedder>, gate: Gatekeeper, policy: VoicePolicy) -> Self {
        Self {
            aec: EchoCanceller::new(),
            book: VoiceBook::new(policy),
            embedder,
            gate,
            last_accepted_ms: None,
        }
    }

    pub fn enroll(&mut self, slug: &str, rows: &[Vec<f32>]) -> BrainResult<()> {
        if self.book.set_person(slug, rows) {
            Ok(())
        } else {
            Err(BrainError::Embedding("enroll"))
        }
    }

    pub fn process(&mut self, frame: &Frame) -> BrainResult<Decision> {
        frame.validate()?;
        let cleaned = self.aec.process(&frame.near, &frame.far)?;
        if cleaned.iter().all(|v| v.abs() < 1.0e-4) {
            return Ok(Decision::Rejected {
                layer: Layer::Aec,
                reason: "echo_only",
            });
        }
        let (speaker, score) = if self.book.is_empty() {
            (None, 0.0)
        } else {
            let probe = self.embedder.embed(&cleaned)?;
            let verdict = self.book.verdict(&probe);
            match verdict.slug {
                Some(slug) if !verdict.ambiguous => (Some(slug), verdict.score),
                Some(_) => {
                    return Ok(Decision::Rejected {
                        layer: Layer::Biometry,
                        reason: "ambiguous_voice",
                    });
                }
                None => {
                    return Ok(Decision::Rejected {
                        layer: Layer::Biometry,
                        reason: "unknown_voice",
                    });
                }
            }
        };
        let since = self
            .last_accepted_ms
            .map(|last| frame.at_ms.saturating_sub(last));
        match self.gate.judge(&frame.transcript, speaker.is_some(), since) {
            GateVerdict::Address => {
                self.last_accepted_ms = Some(frame.at_ms);
                Ok(Decision::Accepted {
                    speaker,
                    text: frame.transcript.clone(),
                    score,
                    at_ms: frame.at_ms,
                })
            }
            GateVerdict::Ignore(reason) => Ok(Decision::Rejected {
                layer: Layer::Gatekeeper,
                reason,
            }),
        }
    }
}

#[derive(Debug, Clone)]
pub struct SharedPipeline {
    inner: Arc<Mutex<SensoryPipeline>>,
}

impl SharedPipeline {
    #[must_use]
    pub fn new(pipeline: SensoryPipeline) -> Self {
        Self {
            inner: Arc::new(Mutex::new(pipeline)),
        }
    }

    pub fn process(&self, frame: &Frame) -> BrainResult<Decision> {
        self.inner
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .process(frame)
    }

    pub fn enroll(&self, slug: &str, rows: &[Vec<f32>]) -> BrainResult<()> {
        self.inner
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .enroll(slug, rows)
    }
}
