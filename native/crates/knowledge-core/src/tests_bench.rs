use std::time::Instant;

use crate::tests::{T0, conv, kn, pid};
use crate::{Kind, Level, Link, NodeRef, Query, Spec};

fn p99(mut samples: Vec<u128>) -> u128 {
    samples.sort_unstable();
    let index = samples
        .len()
        .saturating_mul(99)
        .checked_div(100)
        .unwrap_or(0);
    samples.get(index).copied().unwrap_or(0)
}

fn fill(count: u32) -> crate::Knowledge {
    let mut k = kn();
    let who = pid("nunzio");
    let me = NodeRef {
        kind: Kind::Person,
        label: crate::SELF_KEY.to_owned(),
    };
    for n in 0..count {
        let label = format!("elemento {n} categoria {}", n % 97);
        let spec = Spec {
            kind: Kind::Object,
            label: &label,
            detail: None,
            level: Level::Private,
        };
        assert!(k.remember(&who, &spec, &conv(800), T0).is_ok());
        if n % 4 == 0 {
            let to = NodeRef {
                kind: Kind::Object,
                label,
            };
            let link = Link {
                from: &me,
                relation: "owns",
                to: &to,
                level: Level::Private,
            };
            assert!(k.relate(&who, &link, &conv(800), T0).is_ok());
        }
    }
    k
}

#[test]
#[ignore = "benchmark: cargo test --release -p nuxiva-knowledge-core -- --ignored --nocapture"]
fn search_latency_scales() {
    for count in [1_000_u32, 10_000, 50_000] {
        let start = Instant::now();
        let k = fill(count);
        let build = start.elapsed().as_millis();
        let who = pid("nunzio");
        let samples: Vec<u128> = (0..200_u32)
            .map(|i| {
                let query = Query {
                    text: format!("elemento {} categoria", i % 500),
                    depth: 1,
                    ..Query::default()
                };
                let t = Instant::now();
                let hits = k.search(&who, &query);
                assert!(hits.is_ok());
                t.elapsed().as_micros()
            })
            .collect();
        println!(
            "nodes={count} build_ms={build} search_p99_us={}",
            p99(samples)
        );
    }
}

#[test]
fn search_stays_within_budget_at_five_thousand_nodes() {
    let k = fill(5_000);
    let who = pid("nunzio");
    let query = Query {
        text: "elemento 42 categoria".to_owned(),
        ..Query::default()
    };
    let start = Instant::now();
    for _ in 0..20 {
        assert!(k.search(&who, &query).is_ok());
    }
    assert!(start.elapsed().as_millis() < 5_000);
}
