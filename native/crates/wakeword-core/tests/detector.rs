#![allow(clippy::arithmetic_side_effects)]
#![allow(
    clippy::unreadable_literal,
    clippy::cast_possible_truncation,
    clippy::expect_used,
    clippy::unwrap_used,
    clippy::indexing_slicing,
    clippy::panic,
    clippy::cast_precision_loss
)]

mod support;

use nuxiva_wakeword_core::{Config, Detector, Model, WakeError};
use support::{KEY, OTHER_A, OTHER_B, OTHER_C, concat, noise, pad, to_pcm, word};

fn key_take(pitch: f32, tempo: f32, seed: u64) -> Vec<i16> {
    to_pcm(&pad(
        word(&KEY, pitch, tempo, seed),
        300.0,
        300.0,
        0.003,
        seed + 1,
    ))
}

fn enrolled() -> Model {
    let recordings: Vec<Vec<i16>> = [
        (112.0, 0.92),
        (120.0, 1.0),
        (128.0, 1.06),
        (116.0, 0.97),
        (124.0, 1.03),
    ]
    .iter()
    .enumerate()
    .map(|(i, (p, t))| key_take(*p, *t, 10 + i as u64))
    .collect();
    Model::enroll(&recordings).expect("enroll")
}

fn run(model: &Model, samples: &[f32]) -> usize {
    let mut detector = Detector::new(model.clone(), Config::default()).expect("detector");
    let pcm = to_pcm(samples);
    pcm.chunks(1280).map(|c| detector.push(c).len()).sum()
}

#[test]
fn enrolled_keyword_is_detected_once() {
    let model = enrolled();
    let stream = concat(&[
        noise(0.5, 0.003, 1),
        pad(word(&KEY, 122.0, 1.04, 77), 100.0, 100.0, 0.004, 2),
        noise(1.0, 0.003, 3),
    ]);
    let mut detector = Detector::new(model, Config::default()).expect("detector");
    let hits: Vec<_> = to_pcm(&stream)
        .chunks(1280)
        .flat_map(|c| detector.push(c))
        .collect();
    assert_eq!(hits.len(), 1);
    assert!(hits[0].confidence > 0.3, "{}", hits[0].confidence);
    assert!(hits[0].pcm.len() > 8000);
}

#[test]
fn other_words_never_trigger() {
    let model = enrolled();
    for (i, seg) in [&OTHER_A[..], &OTHER_B[..], &OTHER_C[..]]
        .iter()
        .enumerate()
    {
        for pitch in [105.0, 122.0, 140.0] {
            let stream = pad(word(seg, pitch, 1.0, 40 + i as u64), 400.0, 800.0, 0.003, 9);
            assert_eq!(run(&model, &stream), 0, "word {i} pitch {pitch}");
        }
    }
}

#[test]
fn loud_noise_and_tones_never_trigger() {
    let model = enrolled();
    assert_eq!(run(&model, &noise(4.0, 0.6, 5)), 0);
    let tone: Vec<f32> = (0..64_000).map(|i| 0.5 * (i as f32 * 0.17).sin()).collect();
    assert_eq!(run(&model, &tone), 0);
    let bursts = concat(&[
        noise(0.1, 0.05, 6),
        noise(0.3, 0.9, 7),
        noise(0.8, 0.002, 8),
        noise(0.2, 0.7, 9),
    ]);
    assert_eq!(run(&model, &bursts), 0);
}

#[test]
fn keyword_followed_directly_by_a_command_is_detected() {
    let model = enrolled();
    let stream = concat(&[
        noise(0.5, 0.003, 11),
        word(&KEY, 120.0, 1.0, 21),
        word(&OTHER_A, 120.0, 1.0, 22),
        noise(1.0, 0.003, 12),
    ]);
    assert!(run(&model, &stream) >= 1);
}

#[test]
fn refractory_period_collapses_close_repeats() {
    let model = enrolled();
    let one = |seed| pad(word(&KEY, 121.0, 1.0, seed), 100.0, 100.0, 0.003, seed);
    let close = concat(&[
        noise(0.5, 0.003, 1),
        one(31),
        noise(0.3, 0.003, 2),
        one(32),
        noise(1.0, 0.003, 3),
    ]);
    assert_eq!(run(&model, &close), 1);
    let apart = concat(&[
        noise(0.5, 0.003, 1),
        one(31),
        noise(2.5, 0.003, 2),
        one(32),
        noise(1.0, 0.003, 3),
    ]);
    assert_eq!(run(&model, &apart), 2);
}

#[test]
fn detection_survives_moderate_background_noise() {
    let model = enrolled();
    let stream = concat(&[
        noise(0.6, 0.01, 51),
        pad(word(&KEY, 118.0, 0.98, 52), 0.0, 0.0, 0.01, 53),
        noise(1.0, 0.01, 54),
    ]);
    assert_eq!(run(&model, &stream), 1);
}

#[test]
fn model_serialisation_round_trips_and_rejects_tampering() {
    let model = enrolled();
    let bytes = model.to_bytes();
    assert_eq!(Model::from_bytes(&bytes).expect("parse"), model);
    let mut flipped = bytes.clone();
    flipped[40] ^= 1;
    assert_eq!(Model::from_bytes(&flipped), Err(WakeError::Checksum));
    assert_eq!(
        Model::from_bytes(&bytes[..bytes.len() - 40]),
        Err(WakeError::Checksum)
    );
    assert_eq!(Model::from_bytes(&[]), Err(WakeError::Model));
}

#[test]
fn enrollment_validates_its_inputs() {
    let good = key_take(120.0, 1.0, 1);
    assert_eq!(
        Model::enroll(&[good.clone(), good.clone()]),
        Err(WakeError::TooFewRecordings)
    );
    let silent = vec![0i16; 16_000];
    assert!(matches!(
        Model::enroll(&[good.clone(), good.clone(), silent]),
        Err(WakeError::NoSpeech(2))
    ));
    let short = vec![100i16; 100];
    assert!(matches!(
        Model::enroll(&[good.clone(), good.clone(), short]),
        Err(WakeError::RecordingLength(2))
    ));
    let wrong = to_pcm(&pad(word(&OTHER_B, 120.0, 1.0, 5), 300.0, 300.0, 0.003, 6));
    assert!(matches!(
        Model::enroll(&[
            good.clone(),
            key_take(118.0, 1.0, 2),
            key_take(124.0, 1.02, 3),
            good,
            wrong
        ]),
        Err(WakeError::Inconsistent(4))
    ));
}

#[test]
fn config_is_validated_and_garbage_input_is_safe() {
    let model = enrolled();
    assert!(
        Detector::new(
            model.clone(),
            Config {
                sensitivity: f32::NAN,
                refractory_ms: 1500
            }
        )
        .is_err()
    );
    assert!(
        Detector::new(
            model.clone(),
            Config {
                sensitivity: 9.0,
                refractory_ms: 1500
            }
        )
        .is_err()
    );
    let mut detector = Detector::new(model, Config::default()).expect("detector");
    let mut seed = 7u64;
    for len in [0usize, 1, 3, 159, 401, 4097, 40_000] {
        let junk: Vec<i16> = (0..len)
            .map(|_| {
                seed = seed
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                (seed >> 48) as i16
            })
            .collect();
        let _ = detector.push(&junk);
    }
    detector.reset();
    assert!(detector.push(&[]).is_empty());
}
