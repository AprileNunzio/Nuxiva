#![allow(clippy::indexing_slicing)]

use crate::{Attempt, NextKind, TIERS, evaluate, rank};

const DAY: i64 = 86_400;

fn runs(tier: u8, scores: &[f64], at: i64) -> Vec<Attempt> {
    scores
        .iter()
        .map(|&score| Attempt { tier, score, at })
        .collect()
}

#[test]
fn nothing_done_means_novice_at_the_first_tier() {
    let s = evaluate(&[], 0);
    assert_eq!((s.level, s.rank, s.next.tier), (0, "novice", 0));
    assert_eq!(s.next.kind, NextKind::Advance);
}

#[test]
fn declared_skill_without_evidence_does_not_count() {
    let s = evaluate(&runs(5, &[1.0, 1.0, 1.0], 10), 10);
    assert_eq!(s.level, 0);
}

#[test]
fn passing_tiers_in_order_raises_the_level() {
    let mut list = runs(0, &[0.9, 0.8, 0.9], 10);
    list.extend(runs(1, &[0.75, 0.8, 0.7], 11));
    let s = evaluate(&list, 12);
    assert_eq!(s.level, 2);
    assert_eq!(s.next.tier, 2);
}

#[test]
fn too_few_or_too_weak_attempts_do_not_pass() {
    assert_eq!(evaluate(&runs(0, &[1.0, 1.0], 1), 1).level, 0);
    assert_eq!(evaluate(&runs(0, &[0.5, 0.6, 0.6], 1), 1).level, 0);
}

#[test]
fn only_the_latest_five_attempts_count() {
    let mut list = runs(0, &[0.0, 0.0, 0.0, 0.0, 0.0], 1);
    list.extend(runs(0, &[0.9, 0.9, 0.9, 0.9, 0.9], 2));
    assert_eq!(evaluate(&list, 3).level, 1);
}

#[test]
fn a_stale_tier_is_reviewed_before_advancing() {
    let list = runs(0, &[0.9, 0.9, 0.9], 0);
    let s = evaluate(&list, 40 * DAY);
    assert_eq!(s.level, 1);
    assert_eq!((s.next.tier, s.next.kind), (0, NextKind::Review));
}

#[test]
fn skills_lapse_after_long_inactivity() {
    let list = runs(0, &[0.9, 0.9, 0.9], 0);
    assert_eq!(evaluate(&list, 100 * DAY).level, 0);
}

#[test]
fn hostile_values_are_neutralised() {
    let list = vec![
        Attempt {
            tier: 0,
            score: f64::NAN,
            at: 0,
        },
        Attempt {
            tier: 200,
            score: 1.0,
            at: 0,
        },
        Attempt {
            tier: 0,
            score: 9.0,
            at: i64::MAX,
        },
        Attempt {
            tier: 0,
            score: -4.0,
            at: i64::MIN,
        },
    ];
    let s = evaluate(&list, 0);
    assert!(s.recent_mean.is_finite() && s.level <= TIERS);
}

#[test]
fn mastering_everything_keeps_maintaining() {
    let mut list = Vec::new();
    for tier in 0..TIERS {
        list.extend(runs(tier, &[0.95; 3], 5));
    }
    let s = evaluate(&list, 6);
    assert_eq!(
        (s.level, s.rank, s.next.kind),
        (TIERS, "master", NextKind::Maintain)
    );
}

#[test]
fn ranks_cover_every_level() {
    assert_eq!(rank(0), "novice");
    assert_eq!(rank(4), "proficient");
    assert_eq!(rank(8), "expert");
    assert_eq!(rank(10), "master");
}
