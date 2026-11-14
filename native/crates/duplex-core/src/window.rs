use crate::barge::{BargeSettings, Evidence, Verdict};

pub const KNOWN_BONUS: f32 = 0.12;
pub const MIN_RUNNER_GAP: f32 = 0.10;
pub const WINDOW_MS: u32 = 250;
pub const CONFIRM_WINDOWS: u32 = 3;

#[allow(clippy::struct_excessive_bools)]
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct WindowInput {
    pub voiced: bool,
    pub has_match: bool,
    pub score: f32,
    pub runner_up: f32,
    pub limit: f32,
    pub music: bool,
    pub programme: bool,
    pub echo_cancelled: bool,
}

#[must_use]
pub fn judge_window(input: &WindowInput) -> Evidence {
    let evidence = |verdict, margin_permille| Evidence {
        verdict,
        margin_permille,
        voiced: input.voiced,
        frame_ms: WINDOW_MS,
    };
    let finite = [input.score, input.runner_up, input.limit]
        .iter()
        .all(|v| v.is_finite());
    if !input.voiced || !finite || !input.echo_cancelled {
        return evidence(Verdict::Uncertain, 0);
    }
    if input.music || input.programme {
        return evidence(Verdict::Broadcast, 0);
    }
    let over = input.score - input.limit;
    let gap = input.score - input.runner_up;
    if !input.has_match || over < KNOWN_BONUS || gap < MIN_RUNNER_GAP {
        return evidence(Verdict::Uncertain, 0);
    }
    let permille = (over.clamp(0.0, 1.0) * 1_000.0).round();
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    evidence(Verdict::Known, permille as u16)
}

#[must_use]
pub fn windowed_settings() -> BargeSettings {
    BargeSettings {
        min_voiced_ms: WINDOW_MS.saturating_mul(CONFIRM_WINDOWS),
        duck_after_ms: WINDOW_MS,
        duck_ms: 3_000,
        min_margin_permille: 120,
        guest_may_interrupt: false,
        cooldown_ms: 1_500,
        pre_roll_ms: 600,
    }
}
