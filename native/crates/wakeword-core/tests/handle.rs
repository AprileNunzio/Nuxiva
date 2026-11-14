#![allow(
    clippy::expect_used,
    clippy::unwrap_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::unreadable_literal,
    clippy::cast_sign_loss,
    clippy::many_single_char_names,
    clippy::similar_names
)]

mod support;

use nuxiva_wakeword_core::handle::{self, MAX_PUSH_BYTES};
use nuxiva_wakeword_core::{Model, WakeError};
use support::{KEY, noise, pad, to_pcm, word};

fn model_bytes() -> Vec<u8> {
    let takes: Vec<Vec<i16>> = [(112.0, 0.92), (120.0, 1.0), (128.0, 1.06)]
        .iter()
        .enumerate()
        .map(|(i, (p, t))| {
            to_pcm(&pad(
                word(&KEY, *p, *t, 10 + i as u64),
                300.0,
                300.0,
                0.003,
                11 + i as u64,
            ))
        })
        .collect();
    Model::enroll(&takes).expect("enroll").to_bytes()
}

fn bytes(pcm: &[i16]) -> Vec<u8> {
    pcm.iter().flat_map(|s| s.to_le_bytes()).collect()
}

#[test]
fn handle_lifecycle_detects_through_the_byte_interface() {
    let id = handle::create(&model_bytes(), 1.0).expect("create");
    let stream: Vec<f32> = [
        noise(0.5, 0.003, 1),
        pad(word(&KEY, 122.0, 1.04, 77), 100.0, 100.0, 0.004, 2),
        noise(1.0, 0.003, 3),
    ]
    .concat();
    let raw = bytes(&to_pcm(&stream));
    let mut hits = Vec::new();
    for chunk in raw.chunks(2560) {
        hits.extend(handle::push(id, chunk).expect("push"));
    }
    assert_eq!(hits.len(), 1);
    let encoded = handle::encode(&hits[0]);
    assert_eq!(encoded.len(), 4 + hits[0].pcm.len() * 2);
    assert!(f32::from_le_bytes([encoded[0], encoded[1], encoded[2], encoded[3]]) > 0.3);
    handle::destroy(id);
    assert_eq!(handle::push(id, &[0, 0]).err(), Some(WakeError::Config));
}

#[test]
fn bad_inputs_are_rejected() {
    assert!(handle::create(&[1, 2, 3], 1.0).is_err());
    assert!(handle::create(&model_bytes(), f32::NAN).is_err());
    let id = handle::create(&model_bytes(), 1.0).expect("create");
    assert!(handle::push(id, &[0]).is_err());
    assert!(handle::push(id, &vec![0u8; MAX_PUSH_BYTES + 2]).is_err());
    assert!(handle::push(u64::MAX, &[0, 0]).is_err());
    handle::destroy(id);
    handle::destroy(id);
}
