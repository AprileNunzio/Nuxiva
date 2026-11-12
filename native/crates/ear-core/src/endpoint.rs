#[derive(Debug, Clone, Copy, PartialEq)]
pub struct EndpointConfig {
    pub end_silence: f64,
    pub wake_hold: f64,
    pub wake_tail: f64,
    pub max_utterance: f64,
}

impl Default for EndpointConfig {
    fn default() -> Self {
        Self {
            end_silence: 0.65,
            wake_hold: 1.4,
            wake_tail: 0.45,
            max_utterance: 14.0,
        }
    }
}

impl EndpointConfig {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let pick = |value: f64, lo: f64, hi: f64, fallback: f64| {
            if value.is_finite() {
                value.clamp(lo, hi)
            } else {
                fallback
            }
        };
        let base = Self::default();
        let end_silence = pick(self.end_silence, 0.3, 1.5, base.end_silence);
        Self {
            end_silence,
            wake_hold: pick(
                self.wake_hold,
                end_silence,
                3.0,
                base.wake_hold.max(end_silence),
            ),
            wake_tail: pick(self.wake_tail, 0.1, 2.0, base.wake_tail),
            max_utterance: pick(self.max_utterance, 2.0, 60.0, base.max_utterance),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EndReason {
    Silence,
    WakeHold,
    TooLong,
}

impl EndReason {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Silence => "silence",
            Self::WakeHold => "wake_hold",
            Self::TooLong => "too_long",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Endpointer {
    cfg: EndpointConfig,
    active: bool,
    start: f64,
    last_voice: f64,
    last_frame: f64,
    woke: bool,
    after_wake: f64,
}

impl Endpointer {
    #[must_use]
    pub fn new(cfg: EndpointConfig) -> Self {
        Self {
            cfg: cfg.sanitized(),
            active: false,
            start: 0.0,
            last_voice: 0.0,
            last_frame: 0.0,
            woke: false,
            after_wake: 0.0,
        }
    }

    #[must_use]
    pub fn config(&self) -> EndpointConfig {
        self.cfg
    }

    #[must_use]
    pub fn active(&self) -> bool {
        self.active
    }

    pub fn begin(&mut self, now: f64) {
        self.active = true;
        self.start = now;
        self.last_voice = now;
        self.last_frame = now;
        self.woke = false;
        self.after_wake = 0.0;
    }

    pub fn wake(&mut self) {
        if self.active {
            self.woke = true;
            self.after_wake = 0.0;
        }
    }

    pub fn reset(&mut self) {
        self.active = false;
        self.woke = false;
        self.after_wake = 0.0;
    }

    pub fn frame(&mut self, now: f64, voiced: bool) -> Option<EndReason> {
        if !self.active || !now.is_finite() {
            return None;
        }
        let step = (now - self.last_frame).clamp(0.0, 1.0);
        self.last_frame = now;
        if voiced {
            self.last_voice = now;
            if self.woke {
                self.after_wake += step;
            }
        }
        let reason = if now - self.start > self.cfg.max_utterance {
            Some(EndReason::TooLong)
        } else if self.holding() {
            (now - self.last_voice > self.cfg.wake_hold).then_some(EndReason::WakeHold)
        } else {
            (now - self.last_voice > self.cfg.end_silence).then_some(EndReason::Silence)
        };
        if reason.is_some() {
            self.reset();
        }
        reason
    }

    #[must_use]
    pub fn holding(&self) -> bool {
        self.active && self.woke && self.after_wake < self.cfg.wake_tail
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(ep: &mut Endpointer, from: f64, to: f64, voiced: bool) -> Option<(f64, EndReason)> {
        let mut t = from;
        while t < to {
            if let Some(reason) = ep.frame(t, voiced) {
                return Some((t, reason));
            }
            t += 0.03;
        }
        None
    }

    #[test]
    fn pause_after_the_wake_word_keeps_the_utterance_open() {
        let mut ep = Endpointer::new(EndpointConfig::default());
        ep.begin(0.0);
        assert!(run(&mut ep, 0.0, 0.6, true).is_none());
        ep.wake();
        assert!(run(&mut ep, 0.6, 1.6, false).is_none());
        assert!(run(&mut ep, 1.6, 3.0, true).is_none());
        let (at, reason) = run(&mut ep, 3.0, 5.0, false).unwrap_or((0.0, EndReason::TooLong));
        assert_eq!(reason, EndReason::Silence);
        assert!(at > 3.6 && at < 3.8);
    }

    #[test]
    fn a_lone_wake_word_ends_after_the_hold() {
        let mut ep = Endpointer::new(EndpointConfig::default());
        ep.begin(0.0);
        assert!(run(&mut ep, 0.0, 0.6, true).is_none());
        ep.wake();
        let (at, reason) = run(&mut ep, 0.6, 4.0, false).unwrap_or((0.0, EndReason::TooLong));
        assert_eq!(reason, EndReason::WakeHold);
        assert!(at > 1.9 && at < 2.1);
    }

    #[test]
    fn without_wake_the_normal_silence_applies() {
        let mut ep = Endpointer::new(EndpointConfig::default());
        ep.begin(0.0);
        assert!(run(&mut ep, 0.0, 1.0, true).is_none());
        let (at, reason) = run(&mut ep, 1.0, 3.0, false).unwrap_or((0.0, EndReason::TooLong));
        assert_eq!(reason, EndReason::Silence);
        assert!(at < 1.75);
        assert!(!ep.active());
    }

    #[test]
    fn long_speech_is_cut_and_bad_config_is_clamped() {
        let mut ep = Endpointer::new(EndpointConfig {
            end_silence: f64::NAN,
            wake_hold: 0.1,
            wake_tail: 9.0,
            max_utterance: 3.0,
        });
        let cfg = ep.config();
        assert!((cfg.end_silence - 0.65).abs() < 1e-9);
        assert!(cfg.wake_hold >= cfg.end_silence);
        assert!((cfg.wake_tail - 2.0).abs() < 1e-9);
        ep.begin(0.0);
        let (_, reason) = run(&mut ep, 0.0, 10.0, true).unwrap_or((0.0, EndReason::Silence));
        assert_eq!(reason, EndReason::TooLong);
    }
}
