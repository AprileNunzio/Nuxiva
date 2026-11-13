use std::time::Instant;

use crate::tests::{person, pid, shared};
use crate::{Delta, Lang, Request, Role};

fn p99(mut samples: Vec<u128>) -> u128 {
    samples.sort_unstable();
    let index = samples
        .len()
        .saturating_mul(99)
        .checked_div(100)
        .unwrap_or(0);
    samples.get(index).copied().unwrap_or(0)
}

#[test]
#[ignore = "benchmark: cargo test --release -p nuxiva-context-core -- --ignored --nocapture"]
fn read_and_render_latency() {
    let ctx = shared();
    for n in 0..1_000_u32 {
        let id = format!("p{n}");
        let role = if n % 5 == 0 {
            Role::Guest
        } else {
            Role::Family
        };
        let applied = ctx.apply(Delta::Upsert(Box::new(person(
            &ctx,
            &id,
            &format!("Persona {n}"),
            role,
        ))));
        assert!(applied.is_ok());
    }
    let reads: Vec<u128> = (0..20_000)
        .map(|_| {
            let start = Instant::now();
            let snapshot = ctx.snapshot();
            let found = snapshot.person(&pid("p500")).is_some();
            assert!(found);
            start.elapsed().as_nanos()
        })
        .collect();
    let ids = ["p1", "p2", "p3", "p4"];
    let request = Request {
        subjects: ids.iter().map(|s| pid(s)).collect(),
        present: ids.iter().map(|s| pid(s)).collect(),
        lang: Lang::It,
        budget_chars: 0,
        now_ms: 1,
    };
    let misses: Vec<u128> = (0..2_000_u64)
        .map(|n| {
            let mut fresh = request.clone();
            fresh.now_ms = n.saturating_mul(60_000);
            let start = Instant::now();
            let text = ctx.render(&fresh);
            assert!(!text.is_empty());
            start.elapsed().as_nanos()
        })
        .collect();
    let hits: Vec<u128> = (0..20_000)
        .map(|_| {
            let start = Instant::now();
            let text = ctx.render(&request);
            assert!(!text.is_empty());
            start.elapsed().as_nanos()
        })
        .collect();
    println!(
        "snapshot read p99 {} ns, render 4 persons miss p99 {} ns, hit p99 {} ns",
        p99(reads),
        p99(misses),
        p99(hits)
    );
}
