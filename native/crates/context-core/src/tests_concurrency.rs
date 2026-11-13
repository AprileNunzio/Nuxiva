use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;

use crate::tests::{person, pid, shared};
use crate::{Delta, Lang, Request, Role};

#[test]
fn readers_never_see_torn_state_while_a_writer_updates() {
    let ctx = shared();
    let stop = Arc::new(AtomicBool::new(false));
    let mut readers = Vec::new();
    for _ in 0..16 {
        let ctx = ctx.clone();
        let stop = Arc::clone(&stop);
        readers.push(thread::spawn(move || {
            let mut last = 0_u64;
            let mut reads = 0_u64;
            while !stop.load(Ordering::Relaxed) {
                let snapshot = ctx.snapshot();
                assert!(snapshot.version() >= last);
                last = snapshot.version();
                assert_eq!(
                    u64::try_from(snapshot.len()).unwrap_or(u64::MAX),
                    snapshot.version().min(8),
                );
                let request = Request {
                    subjects: vec![pid("p0")],
                    present: vec![pid("p0")],
                    lang: Lang::It,
                    budget_chars: 0,
                    now_ms: 1,
                };
                let _ = ctx.render(&request);
                reads = reads.saturating_add(1);
            }
            reads
        }));
    }
    for round in 0..1_000_u32 {
        let id = format!("p{}", round % 8);
        let name = format!("Persona {round}");
        let applied = ctx.apply(Delta::Upsert(Box::new(person(
            &ctx,
            &id,
            &name,
            Role::Family,
        ))));
        assert!(applied.is_ok());
    }
    stop.store(true, Ordering::Relaxed);
    let total: u64 = readers
        .into_iter()
        .map(|handle| handle.join().unwrap_or(0))
        .sum();
    assert!(total > 0);
    assert_eq!(ctx.snapshot().version(), 1_000);
}
