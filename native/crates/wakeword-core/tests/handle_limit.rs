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

use nuxiva_wakeword_core::handle::{self, MAX_HANDLES};
use nuxiva_wakeword_core::{Model, WakeError};
use support::{KEY, pad, to_pcm, word};

#[test]
fn handle_count_is_bounded_and_slots_are_reusable() {
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
    let model = Model::enroll(&takes).expect("enroll").to_bytes();
    let ids: Vec<u64> = (0..MAX_HANDLES)
        .map(|_| handle::create(&model, 1.0).expect("create"))
        .collect();
    assert_eq!(handle::create(&model, 1.0), Err(WakeError::Config));
    handle::destroy(ids[0]);
    let again = handle::create(&model, 1.0).expect("slot freed");
    assert!(!ids.contains(&again));
    for id in ids.into_iter().skip(1).chain(std::iter::once(again)) {
        handle::destroy(id);
    }
}
