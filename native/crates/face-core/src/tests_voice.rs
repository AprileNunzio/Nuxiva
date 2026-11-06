#![allow(
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss
)]

use crate::{VoiceError, voice_check};

const RATE: u32 = 16_000;

fn take(seconds: f32, voice: f32, noise: f32, start: f32, stop: f32) -> Vec<i16> {
    let n = (seconds * RATE as f32) as usize;
    let mut seed = 7_u64;
    (0..n)
        .map(|i| {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            let t = i as f32 / RATE as f32;
            let hiss = ((seed % 2000) as f32 / 1000.0 - 1.0) * noise;
            let speak = if t >= start && t <= stop {
                voice * (2.0 * std::f32::consts::PI * 180.0 * t).sin()
            } else {
                0.0
            };
            ((speak + hiss) * 32_767.0).clamp(-32_768.0, 32_767.0) as i16
        })
        .collect()
}

#[test]
fn a_clean_take_scores_high_and_needs_little_gain() {
    let r = voice_check(&take(1.6, 0.14, 0.002, 0.3, 1.2), RATE).unwrap_or_else(|_| unreachable!());
    assert!(r.reasons.is_empty(), "{r:?}");
    assert!(r.score > 75.0, "{r:?}");
    assert!(
        r.snr_db > 25.0 && r.speech_db > -22.0 && r.speech_db < -15.0,
        "{r:?}"
    );
    assert!(r.gain_db.abs() < 4.0, "{r:?}");
    assert!((r.voiced_seconds - 0.9).abs() < 0.1, "{r:?}");
}

#[test]
fn weak_noisy_clipped_and_cut_takes_are_explained() {
    let weak =
        voice_check(&take(1.6, 0.004, 0.0005, 0.3, 1.2), RATE).unwrap_or_else(|_| unreachable!());
    assert!(
        weak.reasons.contains(&"weak") && weak.gain_db >= 23.9,
        "{weak:?}"
    );
    let noisy =
        voice_check(&take(1.6, 0.05, 0.08, 0.3, 1.2), RATE).unwrap_or_else(|_| unreachable!());
    assert!(noisy.reasons.contains(&"noisy"), "{noisy:?}");
    let loud =
        voice_check(&take(1.6, 1.4, 0.002, 0.3, 1.2), RATE).unwrap_or_else(|_| unreachable!());
    assert!(
        loud.reasons.contains(&"clipped") && loud.gain_db < 0.0,
        "{loud:?}"
    );
    let cut =
        voice_check(&take(1.2, 0.14, 0.002, 0.0, 0.9), RATE).unwrap_or_else(|_| unreachable!());
    assert!(cut.reasons.contains(&"truncated"), "{cut:?}");
    assert!(weak.score < 60.0 && noisy.score < 60.0 && loud.score < 60.0);
}

#[test]
fn bad_rates_and_lengths_are_refused() {
    assert_eq!(
        voice_check(&take(1.0, 0.1, 0.0, 0.2, 0.8), 4_000),
        Err(VoiceError::Rate)
    );
    assert_eq!(
        voice_check(&take(0.2, 0.1, 0.0, 0.0, 0.2), RATE),
        Err(VoiceError::Length)
    );
    assert_eq!(voice_check(&[], RATE), Err(VoiceError::Length));
}
