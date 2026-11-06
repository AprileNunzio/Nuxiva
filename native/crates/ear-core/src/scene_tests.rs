use std::f32::consts::PI;

use crate::{SceneClassifier, SoundKind};

const RATE: usize = 16_000;
const FRAME: usize = 480;

struct Rng(u64);

impl Rng {
    fn gauss(&mut self) -> f32 {
        let mut unit = || {
            self.0 ^= self.0 << 13;
            self.0 ^= self.0 >> 7;
            self.0 ^= self.0 << 17;
            #[allow(clippy::cast_precision_loss)]
            let value = (self.0 >> 40) as f32 / (1u64 << 24) as f32;
            value
        };
        let a = unit().max(1e-7);
        let b = unit();
        (-2.0 * a.ln()).sqrt() * (2.0 * PI * b).cos()
    }
}

#[allow(clippy::cast_precision_loss)]
fn speech(len: usize, gain: f32) -> Vec<f32> {
    let mut phase = 0.0_f32;
    (0..len)
        .map(|i| {
            let t = i as f32 / RATE as f32;
            let f0 = 140.0 + 45.0 * (2.0 * PI * 0.9 * t).sin() + 15.0 * (2.0 * PI * 3.1 * t).sin();
            phase += 2.0 * PI * f0 / RATE as f32;
            let syllable = (2.0 * PI * 3.5 * t).sin().max(0.0).powf(0.6);
            let phrase = if (t % 2.2) < 1.7 { 1.0 } else { 0.0 };
            let voice: f32 = (1..=20)
                .map(|h| {
                    let hf = f0 * h as f32;
                    let formant = (-((hf - 650.0) / 350.0).powi(2)).exp()
                        + 0.6 * (-((hf - 1700.0) / 450.0).powi(2)).exp();
                    formant * (phase * h as f32).sin()
                })
                .sum();
            gain * syllable * phrase * voice
        })
        .collect()
}

#[allow(clippy::cast_precision_loss)]
fn music(len: usize, gain: f32) -> Vec<f32> {
    let chords = [
        [261.6_f32, 329.6, 392.0],
        [220.0, 261.6, 329.6],
        [174.6, 220.0, 261.6],
        [196.0, 246.9, 293.7],
    ];
    (0..len)
        .map(|i| {
            let t = i as f32 / RATE as f32;
            #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
            let index = ((t / 0.6) as usize).checked_rem(chords.len()).unwrap_or(0);
            let chord = chords.get(index).copied().unwrap_or([220.0; 3]);
            let tone: f32 = chord
                .iter()
                .map(|f| {
                    (1..=6)
                        .map(|h| (2.0 * PI * f * h as f32 * t).sin() / h as f32)
                        .sum::<f32>()
                })
                .sum();
            let beat = 1.0 + 0.15 * (2.0 * PI * 2.0 * t).sin();
            gain * beat * tone
        })
        .collect()
}

fn noise(len: usize, gain: f32, seed: u64) -> Vec<f32> {
    let mut rng = Rng(seed);
    (0..len).map(|_| gain * rng.gauss()).collect()
}

fn mix(a: &[f32], b: &[f32]) -> Vec<f32> {
    a.iter().zip(b).map(|(x, y)| x + y).collect()
}

fn verdicts(signal: &[f32]) -> Vec<(bool, SoundKind, bool)> {
    let mut scene = SceneClassifier::new();
    signal
        .chunks_exact(FRAME)
        .map(|frame| {
            let v = scene.feed(frame);
            (v.voiced, v.kind, v.music_bed)
        })
        .collect()
}

fn voiced_share(v: &[(bool, SoundKind, bool)], from: usize) -> f32 {
    let tail = v.get(from..).unwrap_or_default();
    #[allow(clippy::cast_precision_loss)]
    let share = tail.iter().filter(|x| x.0).count() as f32 / tail.len().max(1) as f32;
    share
}

#[test]
fn speech_is_heard_from_the_first_syllable() {
    let signal = mix(&speech(RATE * 8, 0.06), &noise(RATE * 8, 0.002, 1));
    let v = verdicts(&signal);
    let first = v.iter().position(|x| x.0).unwrap_or(usize::MAX);
    assert!(first < 6, "first voiced frame {first}");
    assert!(v.iter().all(|x| !x.2), "speech mistaken for music");
    assert!(voiced_share(&v, 0) > 0.3);
}

#[test]
fn music_alone_stops_opening_utterances() {
    let signal = music(RATE * 12, 0.05);
    let v = verdicts(&signal);
    let tail = v.len() / 2;
    assert!(
        voiced_share(&v, tail) < 0.05,
        "voiced {}",
        voiced_share(&v, tail)
    );
    assert!(v.get(tail..).unwrap_or_default().iter().all(|x| x.2));
}

#[test]
fn steady_noise_is_rejected_after_a_moment() {
    let signal = noise(RATE * 4, 0.05, 2);
    let v = verdicts(&signal);
    assert!(voiced_share(&v, 20) < 0.05);
    assert!(
        v.iter()
            .skip(20)
            .all(|x| x.1 == SoundKind::Noise || x.1 == SoundKind::Silence)
    );
}

#[test]
fn speech_over_music_is_still_heard() {
    let bed = music(RATE * 20, 0.02);
    let mut voice = vec![0.0; RATE * 12];
    voice.extend(speech(RATE * 8, 0.09));
    let v = verdicts(&mix(&bed, &voice));
    let during_music = voiced_share(v.get(..RATE * 12 / FRAME).unwrap_or_default(), 200);
    let during_speech = voiced_share(&v, RATE * 12 / FRAME);
    assert!(during_music < 0.05, "music {during_music}");
    assert!(during_speech > 0.25, "speech {during_speech}");
}

#[test]
fn a_fricative_onset_is_not_vetoed() {
    let mut signal = noise(RATE / 5, 0.03, 4);
    signal.extend(speech(RATE * 2, 0.06));
    let v = verdicts(&signal);
    assert!(v.iter().take(5).any(|x| x.0));
}

#[test]
fn speech_in_steady_noise_breaks_through() {
    let hiss = noise(RATE * 9, 0.02, 6);
    let mut voice = vec![0.0; RATE * 3];
    voice.extend(speech(RATE * 6, 0.08));
    let v = verdicts(&mix(&hiss, &voice));
    let start = RATE * 3 / FRAME;
    assert!(voiced_share(v.get(20..start).unwrap_or_default(), 0) < 0.05);
    assert!(
        voiced_share(&v, start) > 0.25,
        "speech {}",
        voiced_share(&v, start)
    );
    assert!(v.iter().all(|x| !x.2));
}
