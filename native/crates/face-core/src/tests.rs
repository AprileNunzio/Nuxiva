#![allow(
    clippy::indexing_slicing,
    clippy::manual_range_contains,
    clippy::arithmetic_side_effects
)]

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
        marks: None,
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

fn project(yaw: f32, depth: f32) -> crate::Landmarks {
    let pts = [
        (-0.5, -0.4, 0.0),
        (0.5, -0.4, 0.0),
        (0.0, 0.1, depth),
        (-0.4, 0.5, 0.0),
        (0.4, 0.5, 0.0),
    ];
    let flat: Vec<f32> = pts
        .iter()
        .flat_map(|(x, y, z): &(f32, f32, f32)| {
            let xr = x * yaw.cos() + z * yaw.sin();
            let zr = -x * yaw.sin() + z * yaw.cos();
            [
                300.0 + 220.0 * xr / (5.0 + zr),
                240.0 + 220.0 * y / (5.0 + zr),
            ]
        })
        .collect();
    crate::Landmarks::from_slice(&flat).unwrap_or_else(|| unreachable!())
}

#[test]
fn a_flat_photo_fits_a_plane_and_a_real_face_does_not() {
    let flat = crate::planar_residual(&project(0.0, 0.0), &project(0.35, 0.0)).unwrap_or(1.0);
    let real = crate::planar_residual(&project(0.0, -0.4), &project(0.35, -0.4)).unwrap_or(0.0);
    assert!(flat < 0.01, "flat {flat}");
    assert!(real > 0.06, "real {real}");
}

#[test]
fn the_tracker_calls_a_turning_real_face_live_and_a_turning_photo_spoof() {
    let mut real = crate::LivenessTracker::new();
    let mut photo = crate::LivenessTracker::new();
    let (mut a, mut b) = (None, None);
    for i in 0..16_u8 {
        let yaw = (f32::from(i) * 0.5).sin() * 0.4;
        let t = f64::from(i) * 0.25;
        a = Some(real.update(project(yaw, -0.4), t, 0.55));
        b = Some(photo.update(project(yaw, 0.0), t, 0.55));
    }
    assert_eq!(a.map(|r| r.state), Some("live"));
    assert_eq!(b.map(|r| r.state), Some("spoof"));
    let mut still = crate::LivenessTracker::new();
    let r = still.update(project(0.0, -0.4), 0.0, 0.55);
    assert_eq!((r.state, r.score), ("unknown", None));
}

fn texture(seed: u64, mole: bool) -> Vec<u8> {
    let mut rng = Noise(seed);
    let mut img = vec![0_u8; 112 * 112];
    for y in 0..112_usize {
        for x in 0..112_usize {
            #[allow(clippy::cast_precision_loss)]
            let base = 110.0
                + 40.0 * ((x as f32 - 55.5) / 9.0).cos() * ((y as f32) / 13.0).cos()
                + rng.next() * 25.0;
            let spot = mole && (24..34).contains(&x) && (52..62).contains(&y);
            #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
            let v = if spot { 25.0 } else { base.clamp(0.0, 255.0) } as u8;
            img[y * 112 + x] = v;
        }
    }
    img
}

fn sig(img: &[u8]) -> Vec<f32> {
    crate::signature(&crate::Gray::new(img, 112, 112).unwrap_or_else(|_| unreachable!()))
}

#[test]
fn distinctive_marks_separate_identical_twins() {
    let rows = person(30, 16, 0.08);
    let anna: Vec<Vec<f32>> = (0..6).map(|i| sig(&texture(100 + i, false))).collect();
    let alba: Vec<Vec<f32>> = (0..6).map(|i| sig(&texture(200 + i, true))).collect();
    assert_eq!(anna[0].len(), crate::MARKS_DIM);
    let mut book = FaceBook::new(DIM, Settings::default());
    book.replace(vec![
        Entry {
            slug: "anna".to_owned(),
            rows: rows.clone(),
            ir: None,
            marks: Some(anna),
            auto: false,
        },
        Entry {
            slug: "alba".to_owned(),
            rows: rows.clone(),
            ir: None,
            marks: Some(alba.clone()),
            auto: false,
        },
    ]);
    let probe = probe_of(&rows, 3, 0.02);
    let plain = book.verdict(&probe, None);
    assert!(plain.ambiguous && plain.twin);
    let with_mole = book.verdict_with_marks(&probe, None, Some(&sig(&texture(300, true))));
    assert_eq!(with_mole.slug.as_deref(), Some("alba"));
    assert_eq!(with_mole.reason, "segni particolari");
    let without = book.verdict_with_marks(&probe, None, Some(&sig(&texture(301, false))));
    assert_ne!(without.slug.as_deref(), Some("alba"));
    let report = book.report();
    let alba_marks = &report
        .iter()
        .find(|r| r.slug == "alba")
        .unwrap_or_else(|| unreachable!())
        .marks;
    assert!(
        alba_marks
            .iter()
            .any(|m| m.region == "cheek" && m.side == "right"),
        "{alba_marks:?}"
    );
}

#[test]
fn quality_flags_dark_blurry_and_small_faces() {
    let marks = project(0.0, -0.4);
    let sharp = texture(5, false);
    let good = crate::assess(
        &crate::Gray::new(&sharp, 112, 112).unwrap_or_else(|_| unreachable!()),
        &marks,
        160.0,
        640.0,
    );
    assert!(good.score > 70.0 && good.issues.is_empty(), "{good:?}");
    assert_eq!(good.kind, "front");
    let dark = vec![8_u8; 112 * 112];
    let bad = crate::assess(
        &crate::Gray::new(&dark, 112, 112).unwrap_or_else(|_| unreachable!()),
        &marks,
        30.0,
        640.0,
    );
    assert!(bad.score < 30.0);
    for issue in ["dark", "blurry", "small"] {
        assert!(bad.issues.contains(&issue), "{issue} {:?}", bad.issues);
    }
    let light = crate::light(&crate::Gray::new(&dark, 112, 112).unwrap_or_else(|_| unreachable!()));
    assert_eq!(crate::frame_issues(&light), vec!["black"]);
    assert_eq!(project(-0.6, -0.4).pose().kind(), "three_left");
}
