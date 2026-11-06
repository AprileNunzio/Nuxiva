#![allow(clippy::indexing_slicing, clippy::manual_range_contains)]

use std::collections::{BTreeMap, BTreeSet};

use crate::{
    Entry, FaceBook, RowsError, Rules, Settings, centroid, decide, decode_rows, dot, encode_rows,
    merge, pair, person_threshold, unit,
};

const DIM: usize = 64;

struct Noise(u64);

impl Noise {
    fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        #[allow(clippy::cast_precision_loss)]
        let v = (self.0 % 20_000) as f32 / 10_000.0 - 1.0;
        v
    }

    fn vector(&mut self) -> Vec<f32> {
        (0..DIM).map(|_| self.next()).collect()
    }
}

fn person(seed: u64, n: usize, noise: f32) -> Vec<Vec<f32>> {
    let mut rng = Noise(seed.wrapping_mul(2_654_435_761).wrapping_add(1));
    let base = unit(&rng.vector());
    (0..n)
        .map(|_| {
            let jitter = rng.vector();
            unit(
                &base
                    .iter()
                    .zip(&jitter)
                    .map(|(b, j)| b + j * noise)
                    .collect::<Vec<_>>(),
            )
        })
        .collect()
}

fn probe_of(rows: &[Vec<f32>], seed: u64, noise: f32) -> Vec<f32> {
    let mut rng = Noise(seed);
    let c = centroid(rows, DIM);
    unit(
        &c.iter()
            .zip(rng.vector())
            .map(|(a, j)| a + j * noise)
            .collect::<Vec<_>>(),
    )
}

fn entry(slug: &str, rows: Vec<Vec<f32>>, auto: bool) -> Entry {
    Entry {
        slug: slug.to_owned(),
        rows,
        ir: None,
        auto,
    }
}

#[test]
fn near_duplicate_frames_never_raise_the_threshold_above_base() {
    let rows = person(1, 30, 0.01);
    let t = person_threshold(&rows, DIM, 0.40);
    assert!((t - 0.40).abs() < 1e-6, "threshold {t}");
}

#[test]
fn varied_photos_lower_the_threshold_within_the_floor() {
    let rows = person(2, 30, 0.22);
    let t = person_threshold(&rows, DIM, 0.40);
    assert!(t <= 0.40 && t >= 0.32 - 1e-6, "threshold {t}");
    assert!((person_threshold(&rows[..3], DIM, 0.40) - 0.40).abs() < 1e-6);
}

#[test]
fn owner_is_recognised_from_a_new_view() {
    let owner = person(3, 20, 0.12);
    let other = person(4, 20, 0.12);
    let probe = probe_of(&owner, 9, 0.08);
    let mut book = FaceBook::new(DIM, Settings::default());
    book.replace(vec![
        entry("nunzio", owner, false),
        entry("anna", other, false),
    ]);
    let v = book.verdict(&probe, None);
    assert_eq!(v.slug.as_deref(), Some("nunzio"));
    assert!(!v.ambiguous);
    assert!(book.may_learn("nunzio", &probe, None));
}

#[test]
fn an_auto_guest_built_from_the_owner_is_a_shadow_and_does_not_block_recognition() {
    let owner = person(5, 20, 0.12);
    let shadow = person(5, 12, 0.14);
    let probe = probe_of(&owner, 11, 0.05);
    let mut book = FaceBook::new(DIM, Settings::default());
    book.replace(vec![
        entry("nunzio", owner, false),
        entry("ospite-1", shadow, true),
    ]);
    let shadows = book.shadows();
    assert_eq!(shadows.len(), 1);
    assert_eq!(
        (shadows[0].0.as_str(), shadows[0].1.as_str()),
        ("ospite-1", "nunzio")
    );
    let v = book.verdict(&probe, None);
    assert_eq!(v.slug.as_deref(), Some("nunzio"));
    assert!(!v.ambiguous);
}

#[test]
fn named_look_alikes_stay_ambiguous_without_a_clear_margin() {
    let mut scores = BTreeMap::new();
    scores.insert("a".to_owned(), 0.70_f32);
    scores.insert("b".to_owned(), 0.64_f32);
    let limits = BTreeMap::new();
    let twins: BTreeSet<_> = [pair("a", "b")].into_iter().collect();
    let rules = Rules {
        base: 0.4,
        margin: 0.05,
        twin_margin: 0.12,
    };
    let v = decide(&scores, &limits, rules, &twins, &BTreeMap::new(), false);
    assert!(v.ambiguous && v.twin && v.slug.is_none());
    scores.insert("b".to_owned(), 0.50);
    let v = decide(&scores, &limits, rules, &twins, &BTreeMap::new(), false);
    assert_eq!(v.slug.as_deref(), Some("a"));
}

#[test]
fn rows_roundtrip_and_reject_bad_input() {
    let rows = person(6, 3, 0.1);
    let bytes = encode_rows(&rows);
    let back = decode_rows(&bytes, DIM).unwrap_or_default();
    assert_eq!(back.len(), 3);
    assert!((dot(&back[0], &rows[0]) - 1.0).abs() < 1e-5);
    assert_eq!(decode_rows(&bytes[1..], DIM), Err(RowsError::Misaligned));
    assert_eq!(decode_rows(&bytes, 4), Err(RowsError::Dimension));
}

#[test]
fn merge_keeps_the_limit_and_the_newest_sample() {
    let old = person(7, 10, 0.01);
    let fresh = person(8, 1, 0.01);
    let newest = fresh[0].clone();
    let kept = merge(old, fresh, 6);
    assert_eq!(kept.len(), 6);
    assert!(kept.iter().any(|r| (dot(r, &newest) - 1.0).abs() < 1e-6));
}
