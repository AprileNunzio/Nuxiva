#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum VocalStreamPhase {
    Idle,
    EmittingFiller,
    SpeakingReply,
    Interrupted,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VocalStreamState {
    pub phase: VocalStreamPhase,
    pub current_text: String,
    pub started_at_ms: u64,
    pub residual_context: Option<String>,
}

impl Default for VocalStreamState {
    fn default() -> Self {
        Self {
            phase: VocalStreamPhase::Idle,
            current_text: String::new(),
            started_at_ms: 0,
            residual_context: None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum BargeResolution {
    IgnoredNoise,
    AcknowledgedInterruption {
        semantic_token: String,
        previous_text: String,
    },
    ImmediateAbort,
}

#[derive(Debug, Clone)]
pub struct DuplexBargeRouter {
    state: VocalStreamState,
}

impl Default for DuplexBargeRouter {
    fn default() -> Self {
        Self::new()
    }
}

impl DuplexBargeRouter {
    #[must_use]
    pub fn new() -> Self {
        Self {
            state: VocalStreamState::default(),
        }
    }

    pub fn start_speaking(&mut self, text: &str, phase: VocalStreamPhase, now_ms: u64) {
        self.state = VocalStreamState {
            phase,
            current_text: text.to_owned(),
            started_at_ms: now_ms,
            residual_context: None,
        };
    }

    pub fn finish_speaking(&mut self) {
        self.state = VocalStreamState::default();
    }

    #[must_use]
    pub fn current_state(&self) -> &VocalStreamState {
        &self.state
    }

    #[must_use]
    pub fn handle_barge_in(&mut self, incoming_utterance: &str, now_ms: u64) -> BargeResolution {
        if self.state.phase == VocalStreamPhase::Idle {
            return BargeResolution::IgnoredNoise;
        }

        let previous = self.state.current_text.clone();
        self.state.phase = VocalStreamPhase::Interrupted;
        self.state.residual_context = Some(previous.clone());
        self.state.started_at_ms = now_ms;

        let trimmed = incoming_utterance.trim();
        let words: Vec<&str> = trimmed.split_whitespace().collect();

        // Algorithmic check: if short single word <= 4 chars or cancellation intent
        if words.len() <= 1 && trimmed.len() <= 5 {
            return BargeResolution::ImmediateAbort;
        }

        BargeResolution::AcknowledgedInterruption {
            semantic_token: "conversation.interruption_steer".to_owned(),
            previous_text: previous,
        }
    }
}
