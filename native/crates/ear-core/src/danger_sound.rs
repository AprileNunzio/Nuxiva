use crate::sound_frame::{SoundFrame, describe};
use crate::stft::{HOP, N_FFT, RATE, Spectrum, Stft};

pub const MAX_FEED: usize = 16_000 * 30;
const HOP_S: f64 = 256.0 / 16_000.0;
const FLOOR_INIT: f32 = 0.003;
const FLOOR_DOWN: f32 = 0.05;
const FLOOR_RISE: f32 = 1.001;
const SCREAM_OVER: f32 = 12.0;
const SCREAM_MIN_RMS: f32 = 0.04;
const SCREAM_LOW_HZ: f32 = 350.0;
const SCREAM_HIGH_HZ: f32 = 3_200.0;
const SCREAM_CENTROID: f32 = 1_000.0;
const SCREAM_FLAT: f32 = 0.35;
const SCREAM_LOW_SHARE: f32 = 0.3;
const SCREAM_MIN_HOPS: usize = 18;
const SCREAM_MAX_HOPS: usize = 190;
const SCREAM_GAP: usize = 3;
const SCREAM_VIBRATO_CENTS: f64 = 15.0;
const TONE_OVER: f32 = 4.0;
const TONE_SHARE: f32 = 0.35;
const TONE_LOW_HZ: f32 = 2_500.0;
const TONE_HIGH_HZ: f32 = 4_000.0;
const BEEP_MIN_S: f64 = 0.05;
const BEEP_MAX_S: f64 = 0.9;
const GROUP_GAP_S: f64 = 0.9;
const GROUP_END_S: f64 = 1.0;
const GROUP_STALE_S: f64 = 30.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DangerKind {
    Scream,
    SmokeAlarm,
    CoAlarm,
}

impl DangerKind {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Scream => "scream",
            Self::SmokeAlarm => "smoke_alarm",
            Self::CoAlarm => "co_alarm",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SoundEvent {
    pub kind: DangerKind,
    pub probability: f64,
    pub confidence: f64,
    pub at_s: f64,
    pub duration_s: f64,
}

#[derive(Debug, Default)]
struct Run {
    hops: usize,
    hits: usize,
    gap: usize,
    pitches: Vec<f64>,
    harmonic: usize,
    over_db: f64,
    start: f64,
}

#[derive(Debug)]
pub struct DangerSound {
    stft: Stft,
    spectrum: Spectrum,
    window: Vec<f32>,
    pending: Vec<f32>,
    floor: f32,
    hop: u64,
    run: Option<Run>,
    tone_on: Option<f64>,
    tone_off: Option<f64>,
    beeps: usize,
    groups: Vec<(usize, f64)>,
}

impl Default for DangerSound {
    fn default() -> Self {
        Self::new()
    }
}

fn cents_spread(pitches: &[f64]) -> f64 {
    if pitches.len() < 2 {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)]
    let n = pitches.len() as f64;
    let cents: Vec<f64> = pitches.iter().map(|p| 1200.0 * p.max(1.0).log2()).collect();
    let mean = cents.iter().sum::<f64>() / n;
    (cents.iter().map(|c| (c - mean).powi(2)).sum::<f64>() / n).sqrt()
}

impl DangerSound {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stft: Stft::new(),
            spectrum: Stft::empty_spectrum(),
            window: vec![0.0; N_FFT],
            pending: Vec::with_capacity(HOP),
            floor: FLOOR_INIT,
            hop: 0,
            run: None,
            tone_on: None,
            tone_off: None,
            beeps: 0,
            groups: Vec::new(),
        }
    }

    #[must_use]
    pub fn floor(&self) -> f32 {
        self.floor
    }

    #[allow(clippy::cast_precision_loss)]
    fn now(&self) -> f64 {
        self.hop as f64 * HOP_S
    }

    pub fn feed(&mut self, samples: &[f32], media: bool) -> Vec<SoundEvent> {
        let mut out = Vec::new();
        for &s in samples.iter().take(MAX_FEED) {
            self.pending.push(if s.is_finite() {
                s.clamp(-1.0, 1.0)
            } else {
                0.0
            });
            if self.pending.len() == HOP {
                self.window.copy_within(HOP.., 0);
                if let Some(tail) = self.window.get_mut(N_FFT - HOP..) {
                    tail.copy_from_slice(&self.pending);
                }
                self.pending.clear();
                self.hop = self.hop.saturating_add(1);
                let frame = if self.stft.analyze(&self.window, &mut self.spectrum) {
                    describe(
                        self.window.get(N_FFT - HOP..).unwrap_or(&[]),
                        &self.spectrum,
                    )
                } else {
                    SoundFrame::default()
                };
                self.step(&frame, media, &mut out);
            }
        }
        out
    }

    fn screamy(&self, f: &SoundFrame) -> bool {
        f.rms >= SCREAM_MIN_RMS
            && f.rms >= self.floor * SCREAM_OVER
            && (SCREAM_LOW_HZ..=SCREAM_HIGH_HZ).contains(&f.peak_hz)
            && f.centroid_hz >= SCREAM_CENTROID
            && f.flatness <= SCREAM_FLAT
            && f.low_share <= SCREAM_LOW_SHARE
    }

    fn tone(&self, f: &SoundFrame) -> bool {
        f.rms >= self.floor * TONE_OVER
            && (TONE_LOW_HZ..=TONE_HIGH_HZ).contains(&f.peak_hz)
            && f.peak_share >= TONE_SHARE
            && f.peaks <= 2
    }

    fn step(&mut self, f: &SoundFrame, media: bool, out: &mut Vec<SoundEvent>) {
        let now = self.now();
        let scream = self.screamy(f);
        let tone = self.tone(f);
        if !scream && !tone {
            if f.rms < self.floor {
                self.floor = self.floor * (1.0 - FLOOR_DOWN) + f.rms * FLOOR_DOWN;
            } else {
                self.floor = (self.floor * FLOOR_RISE).min(f.rms.max(FLOOR_INIT * 0.1));
            }
            self.floor = self.floor.max(1e-5);
        }
        self.track_scream(f, scream, now, media, out);
        self.track_tone(tone, now, out);
    }

    fn track_scream(
        &mut self,
        f: &SoundFrame,
        hit: bool,
        now: f64,
        media: bool,
        out: &mut Vec<SoundEvent>,
    ) {
        if hit {
            let over = 20.0 * f64::from((f.rms / self.floor.max(1e-6)).max(1.0)).log10();
            let run = self.run.get_or_insert_with(|| Run {
                start: now,
                ..Run::default()
            });
            run.hops = run.hops.saturating_add(1).saturating_add(run.gap);
            run.hits = run.hits.saturating_add(1);
            run.gap = 0;
            run.pitches.push(f64::from(f.peak_hz));
            if f.peaks >= 2 {
                run.harmonic = run.harmonic.saturating_add(1);
            }
            run.over_db = run.over_db.max(over);
            if run.hops >= SCREAM_MAX_HOPS {
                self.close_scream(now, media, out);
            }
            return;
        }
        let ended = match self.run.as_mut() {
            Some(run) => {
                run.gap = run.gap.saturating_add(1);
                run.gap > SCREAM_GAP
            }
            None => false,
        };
        if ended {
            self.close_scream(now, media, out);
        }
    }

    fn close_scream(&mut self, now: f64, media: bool, out: &mut Vec<SoundEvent>) {
        let Some(run) = self.run.take() else { return };
        if run.hits < SCREAM_MIN_HOPS {
            return;
        }
        #[allow(clippy::cast_precision_loss)]
        let (hits, hops) = (run.hits as f64, run.hops.max(1) as f64);
        let living = cents_spread(&run.pitches) >= SCREAM_VIBRATO_CENTS
            || run.harmonic.saturating_mul(2) >= run.hits;
        if !living {
            return;
        }
        let duration = hops * HOP_S;
        let length = ((duration - 0.3) / 0.7).clamp(0.0, 1.0);
        let loud = ((run.over_db - 22.0) / 15.0).clamp(0.0, 1.0);
        let mut probability = (0.5 + 0.25 * length + 0.2 * loud).clamp(0.0, 0.95);
        if media {
            probability *= 0.5;
        }
        out.push(SoundEvent {
            kind: DangerKind::Scream,
            probability,
            confidence: (hits / hops).clamp(0.0, 1.0) * if media { 0.5 } else { 0.85 },
            at_s: run.start.min(now),
            duration_s: duration,
        });
    }

    fn track_tone(&mut self, tone: bool, now: f64, out: &mut Vec<SoundEvent>) {
        match (tone, self.tone_on) {
            (true, None) => {
                self.tone_on = Some(now);
            }
            (false, Some(start)) => {
                let length = now - start;
                self.tone_on = None;
                if (BEEP_MIN_S..=BEEP_MAX_S).contains(&length) {
                    let joined = self.tone_off.is_some_and(|off| start - off <= GROUP_GAP_S);
                    self.beeps = if joined {
                        self.beeps.saturating_add(1)
                    } else {
                        1
                    };
                } else {
                    self.beeps = 0;
                }
                self.tone_off = Some(now);
            }
            _ => {}
        }
        let quiet_for = self.tone_off.map_or(0.0, |off| now - off);
        if self.tone_on.is_none() && self.beeps > 0 && quiet_for > GROUP_END_S {
            let beeps = std::mem::take(&mut self.beeps);
            self.groups.retain(|(_, at)| now - at <= GROUP_STALE_S);
            if beeps == 3 || beeps == 4 {
                self.groups.push((beeps, now));
                let kind = if beeps == 3 {
                    DangerKind::SmokeAlarm
                } else {
                    DangerKind::CoAlarm
                };
                let repeated = self.groups.iter().filter(|(b, _)| *b == beeps).count();
                let probability = if repeated >= 2 { 0.9 } else { 0.6 };
                out.push(SoundEvent {
                    kind,
                    probability,
                    confidence: if repeated >= 2 { 0.9 } else { 0.6 },
                    at_s: now,
                    duration_s: quiet_for,
                });
            }
        }
    }
}

#[allow(clippy::cast_precision_loss)]
#[must_use]
pub fn seconds_of(samples: usize) -> f64 {
    samples as f64 / f64::from(RATE)
}
