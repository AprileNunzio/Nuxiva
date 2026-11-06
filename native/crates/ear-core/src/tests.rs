use std::f32::consts::PI;

use crate::{
    Denoiser, DenoiserConfig, HOP, NoiseTracker, clean_utterance, exp_integral, normalize,
    omlsa_gain, utterance_gain,
};

const RATE: usize = 16_000;

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        #[allow(clippy::cast_precision_loss)]
        let unit = (self.0 >> 40) as f32 / (1u64 << 24) as f32;
        unit
    }

    fn gauss(&mut self) -> f32 {
        let a = self.next().max(1e-7);
        let b = self.next();
        (-2.0 * a.ln()).sqrt() * (2.0 * PI * b).cos()
    }
}

#[allow(clippy::cast_precision_loss)]
fn speech_like(len: usize) -> Vec<f32> {
    let mut phase = 0.0_f32;
    (0..len)
        .map(|i| {
            let t = i as f32 / RATE as f32;
            let f0 = 150.0 + 40.0 * (2.0 * PI * 0.7 * t).sin();
            phase += 2.0 * PI * f0 / RATE as f32;
            let syllable = (2.0 * PI * 4.0 * t).sin().max(0.0).powf(0.6);
            let voice: f32 = (1..=20)
                .map(|h| {
                    let hf = f0 * h as f32;
                    let formant = (-((hf - 700.0) / 400.0).powi(2)).exp()
                        + 0.6 * (-((hf - 1800.0) / 500.0).powi(2)).exp();
                    formant * (phase * h as f32).sin()
                })
                .sum();
            0.08 * syllable * voice
        })
        .collect()
}

fn energy(x: &[f32]) -> f64 {
    x.iter().map(|v| f64::from(*v) * f64::from(*v)).sum()
}

fn snr(clean: &[f32], test: &[f32]) -> f64 {
    let err: Vec<f32> = clean.iter().zip(test).map(|(a, b)| a - b).collect();
    10.0 * (energy(clean) / energy(&err).max(1e-20)).log10()
}

fn run(denoiser: &mut Denoiser, input: &[f32], chunk: usize) -> Vec<f32> {
    let mut out = Vec::new();
    for part in input.chunks(chunk) {
        denoiser.process(part, &mut out);
    }
    out
}

#[test]
fn exp_integral_matches_reference_values() {
    for (x, want) in [
        (0.1_f32, 1.822_924),
        (0.5, 0.559_774),
        (1.0, 0.219_384),
        (3.0, 0.013_048),
    ] {
        assert!((exp_integral(x) - want).abs() < 2e-4, "E1({x})");
    }
    assert!(omlsa_gain(100.0, 120.0, 0.02, 0.15) > 0.95);
    assert!((omlsa_gain(0.003, 1.0, 0.98, 0.15) - 0.15).abs() < 0.02);
}

#[test]
fn transparent_when_suppression_is_off() {
    #[allow(clippy::cast_precision_loss)]
    let tone: Vec<f32> = (0..RATE * 2)
        .map(|i| 0.3 * (2.0 * PI * 440.0 * i as f32 / RATE as f32).sin())
        .collect();
    let mut d = Denoiser::new(DenoiserConfig {
        suppress: false,
        ..DenoiserConfig::default()
    });
    let out = run(&mut d, &tone, 960);
    let worst = out
        .iter()
        .zip(&tone)
        .skip(HOP)
        .map(|(a, b)| (a - b).abs())
        .fold(0.0_f32, f32::max);
    assert!(worst < 0.01, "worst {worst}");
}

#[test]
fn dc_and_hum_are_removed() {
    #[allow(clippy::cast_precision_loss)]
    let hum: Vec<f32> = (0..RATE * 3)
        .map(|i| 0.08 + 0.05 * (2.0 * PI * 50.0 * i as f32 / RATE as f32).sin())
        .collect();
    let out = run(&mut Denoiser::new(DenoiserConfig::default()), &hum, 480);
    let tail = out.get(RATE..).unwrap_or_default();
    #[allow(clippy::cast_precision_loss)]
    let level = (energy(tail) / tail.len() as f64).sqrt();
    assert!(level < 0.005, "level {level}");
}

#[test]
fn chunking_does_not_change_the_result() {
    let mut rng = Rng(7);
    let input: Vec<f32> = speech_like(RATE * 2)
        .into_iter()
        .map(|v| v + 0.02 * rng.gauss())
        .collect();
    let a = run(&mut Denoiser::new(DenoiserConfig::default()), &input, 480);
    let b = run(&mut Denoiser::new(DenoiserConfig::default()), &input, 1237);
    let len = a.len().min(b.len());
    assert!(len > RATE * 2 - 1024);
    assert_eq!(a.get(..len), b.get(..len));
}

fn improvement(level: f32, seed: u64) -> (f64, f64) {
    let mut rng = Rng(seed);
    let clean = speech_like(RATE * 5);
    let noisy: Vec<f32> = clean.iter().map(|v| v + level * rng.gauss()).collect();
    let mut tracker = NoiseTracker::new();
    let noise_only: Vec<f32> = (0..RATE).map(|_| level * rng.gauss()).collect();
    tracker.learn(&noise_only);
    let out = clean_utterance(&noisy, tracker.psd(), DenoiserConfig::default());
    assert_eq!(out.len(), noisy.len());
    let region = RATE..RATE * 5;
    let reference = clean.get(region.clone()).unwrap_or_default();
    (
        snr(reference, noisy.get(region.clone()).unwrap_or_default()),
        snr(reference, out.get(region).unwrap_or_default()),
    )
}

#[test]
fn noisy_speech_gets_cleaner() {
    let (before, after) = improvement(0.06, 42);
    assert!(after > before + 4.0, "before {before} after {after}");
    let (before, after) = improvement(0.1, 5);
    assert!(after > before + 5.0, "before {before} after {after}");
    let (before, after) = improvement(0.025, 11);
    assert!(after > before, "before {before} after {after}");
}

#[test]
fn stationary_noise_alone_is_strongly_reduced() {
    let mut rng = Rng(3);
    let noise: Vec<f32> = (0..RATE * 4).map(|_| 0.03 * rng.gauss()).collect();
    let out = run(&mut Denoiser::new(DenoiserConfig::default()), &noise, 960);
    let tail_in = noise.get(RATE * 2..RATE * 4).unwrap_or_default();
    let tail_out = out.get(RATE * 2..RATE * 4 - HOP).unwrap_or_default();
    let ratio = 10.0 * (energy(tail_out) / energy(tail_in)).log10();
    assert!(ratio < -12.0, "reduction {ratio}");
}

#[test]
fn restart_keeps_noise_but_drops_stream() {
    let mut rng = Rng(9);
    let mut d = Denoiser::new(DenoiserConfig::default());
    let noise: Vec<f32> = (0..RATE).map(|_| 0.01 * rng.gauss()).collect();
    let _ = run(&mut d, &noise, 480);
    let before = d.noise().to_vec();
    let _ = run(&mut d, &[0.1; 100], 100);
    d.restart();
    assert_eq!(d.pending(), 0);
    assert_eq!(d.noise(), before.as_slice());
}

#[test]
fn level_normalisation_matches_reference_rules() {
    let loud = vec![2.5_f32; 1000];
    assert!(
        normalize(&loud, 0.075, 18.0)
            .iter()
            .all(|v| v.abs() <= 0.97)
    );
    assert!((utterance_gain(&[0.0; 640], 0.075, 18.0) - 1.0).abs() < 1e-12);
    assert!((utterance_gain(&[0.01_f32; 3200], 0.075, 18.0) - 1.0).abs() < 1e-12);
    #[allow(clippy::cast_precision_loss)]
    let ramp: Vec<f32> = (0..3200)
        .map(|i| 0.001 * ((i / 320) as f32 + 1.0))
        .collect();
    assert!((utterance_gain(&ramp, 0.075, 18.0) - 0.075 / 0.0085).abs() < 1e-3);
    let nan = vec![f32::NAN; 10];
    assert!(normalize(&nan, 0.075, 18.0).iter().all(|v| v.is_finite()));
}
