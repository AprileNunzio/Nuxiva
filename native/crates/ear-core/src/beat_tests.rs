use std::f32::consts::PI;

use crate::{SceneClassifier, SoundKind};

const RATE: usize = 16_000;
const FRAME: usize = 480;

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        #[allow(clippy::cast_precision_loss)]
        let v = (self.0 >> 40) as f32 / (1u64 << 24) as f32 - 0.5;
        v
    }
}

#[allow(clippy::cast_precision_loss)]
fn song(len: usize, gain: f32, bpm: f32) -> Vec<f32> {
    let mut rng = Rng(7);
    let beat = 60.0 / bpm;
    let mut phase = 0.0_f32;
    (0..len)
        .map(|i| {
            let t = i as f32 / RATE as f32;
            let since = t % beat;
            let kick = (-since * 18.0).exp() * (2.0 * PI * 70.0 * since).sin();
            let half = (t + beat / 2.0) % beat;
            let hat = (-half * 60.0).exp() * rng.next();
            let melody =
                330.0 + 90.0 * (2.0 * PI * 0.37 * t).sin() + 40.0 * (2.0 * PI * 1.1 * t).sin();
            phase += 2.0 * PI * melody / RATE as f32;
            let sung: f32 = (1..=8).map(|h| (phase * h as f32).sin() / h as f32).sum();
            gain * (1.6 * kick + 0.5 * hat + 0.35 * sung)
        })
        .collect()
}

#[allow(clippy::cast_precision_loss)]
fn talk(len: usize, gain: f32) -> Vec<f32> {
    let mut phase = 0.0_f32;
    (0..len)
        .map(|i| {
            let t = i as f32 / RATE as f32;
            let f0 = 120.0 + 40.0 * (2.0 * PI * 0.8 * t).sin();
            phase += 2.0 * PI * f0 / RATE as f32;
            let syllable = (2.0 * PI * 3.8 * t).sin().max(0.0);
            let phrase = if (t % 3.1) < 2.2 { 1.0 } else { 0.0 };
            let voice: f32 = (1..=14).map(|h| (phase * h as f32).sin() / h as f32).sum();
            gain * syllable * phrase * voice
        })
        .collect()
}

fn music_share(signal: &[f32], from: usize) -> f32 {
    let mut scene = SceneClassifier::new();
    let kinds: Vec<(SoundKind, bool)> = signal
        .chunks_exact(FRAME)
        .map(|f| {
            let v = scene.feed(f);
            (v.kind, v.music_bed)
        })
        .collect();
    let tail = kinds.get(from..).unwrap_or_default();
    #[allow(clippy::cast_precision_loss)]
    let share = tail
        .iter()
        .filter(|(k, bed)| *bed || *k == SoundKind::Music)
        .count() as f32
        / tail.len().max(1) as f32;
    share
}

#[test]
fn a_song_with_drums_and_a_moving_voice_is_music() {
    for bpm in [84.0, 100.0, 120.0, 128.0, 140.0] {
        let share = music_share(&song(RATE * 30, 0.08, bpm), 20 * RATE / FRAME);
        assert!(share > 0.8, "bpm {bpm} share {share}");
    }
}

#[test]
fn spoken_radio_with_pauses_is_not_taken_for_a_song() {
    let share = music_share(&talk(RATE * 30, 0.08), 20 * RATE / FRAME);
    assert!(share < 0.1, "share {share}");
}

#[test]
fn a_song_is_not_music_before_enough_evidence() {
    let share = music_share(&song(RATE * 4, 0.08, 120.0), 0);
    assert!(share < 0.5, "share {share}");
}
