#![allow(clippy::indexing_slicing)]

use crate::{Archive, NewEntry, shard, tokens};

fn digest(n: u32) -> String {
    format!("{n:08x}").repeat(8)
}

fn put(a: &mut Archive, key: &str, n: u32, tags: &[&str], now: i64) {
    let entry = NewEntry {
        key: key.to_owned(),
        digest: digest(n),
        kind: "particles".to_owned(),
        meta: "{}".to_owned(),
        tags: tags.iter().map(|t| (*t).to_owned()).collect(),
    };
    assert!(a.put(&entry, now).is_ok(), "{key}");
}

fn memory() -> Archive {
    Archive::open_memory().unwrap_or_else(|e| unreachable!("{e}"))
}

#[test]
fn put_lookup_and_reuse_counter() {
    let mut a = memory();
    put(&mut a, "medusa", 1, &["cnidario"], 10);
    let first = a.lookup("medusa", 20).ok().flatten();
    assert_eq!(
        first.as_ref().map(|e| (e.uses, e.last, e.created)),
        Some((2, 20, 10))
    );
    put(&mut a, "medusa", 2, &["cnidario"], 30);
    let again = a.lookup("medusa", 40).ok().flatten();
    assert_eq!(
        again
            .as_ref()
            .map(|e| (e.digest.clone(), e.uses, e.created)),
        Some((digest(2), 3, 10))
    );
    assert_eq!(a.count().ok(), Some(1));
    assert!(a.lookup("assente", 1).ok().flatten().is_none());
}

#[test]
fn search_finds_by_prefix_tag_and_ranks_by_use() {
    let mut a = memory();
    put(&mut a, "medusa lunare", 1, &["animale", "mare"], 1);
    put(&mut a, "medusa cassiopea", 2, &["animale"], 2);
    put(&mut a, "motore v8", 3, &["auto", "meccanica"], 3);
    let _ = a.lookup("medusa cassiopea", 5);
    let hits = a.search("medus", 10).unwrap_or_default();
    assert_eq!(
        hits.iter().map(|h| h.key.as_str()).collect::<Vec<_>>(),
        ["medusa cassiopea", "medusa lunare"]
    );
    assert_eq!(
        a.search("meccanica", 10)
            .unwrap_or_default()
            .first()
            .map(|h| h.key.as_str()),
        Some("motore v8")
    );
    assert!(a.search("zzz", 10).unwrap_or_default().is_empty());
}

#[test]
fn hostile_queries_are_harmless() {
    let mut a = memory();
    put(&mut a, "medusa", 1, &[], 1);
    for query in [
        "\"",
        "*",
        "medusa\" OR \"x",
        "NEAR(a b)",
        "a) OR (b",
        "'; DROP TABLE creations; --",
        "",
        "   ",
        "key:medusa",
        "-medusa",
        &"a".repeat(10_000),
    ] {
        assert!(a.search(query, 5).is_ok(), "{query}");
    }
    assert_eq!(a.count().ok(), Some(1));
    assert_eq!(a.search("key:medusa", 5).unwrap_or_default().len(), 1);
    assert_eq!(a.search("medusa", usize::MAX).unwrap_or_default().len(), 1);
}

#[test]
fn invalid_entries_are_refused() {
    let mut a = memory();
    let good = NewEntry {
        key: "k".to_owned(),
        digest: digest(1),
        kind: "p".to_owned(),
        meta: String::new(),
        tags: Vec::new(),
    };
    assert!(a.put(&good, 1).is_ok());
    for bad in [
        NewEntry {
            key: String::new(),
            ..good.clone()
        },
        NewEntry {
            key: "x".repeat(121),
            ..good.clone()
        },
        NewEntry {
            digest: "ABC".to_owned(),
            ..good.clone()
        },
        NewEntry {
            digest: "../../etc/passwd".repeat(5),
            ..good.clone()
        },
        NewEntry {
            kind: String::new(),
            ..good.clone()
        },
        NewEntry {
            meta: "x".repeat(20_000),
            ..good.clone()
        },
    ] {
        assert!(a.put(&bad, 1).is_err());
    }
}

#[test]
fn eviction_keeps_the_most_recent_and_reports_orphan_blobs() {
    let mut a = memory();
    for n in 0..10_u32 {
        put(&mut a, &format!("forma {n}"), n, &[], i64::from(n));
    }
    put(&mut a, "forma gemella", 0, &[], 100);
    let gone = a.evict(5).unwrap_or_default();
    assert_eq!(a.count().ok(), Some(5));
    assert!(!gone.contains(&digest(0)));
    assert!(gone.contains(&digest(1)));
    assert!(a.search("forma", 100).unwrap_or_default().len() <= 5);
    assert_eq!(a.recent(2).unwrap_or_default().len(), 2);
}

#[test]
fn shards_and_tokens_are_strict() {
    assert_eq!(
        shard(&digest(0xabcd_ef01)).as_deref(),
        Some(format!("ab/cd/{}", digest(0xabcd_ef01)).as_str())
    );
    assert!(
        shard("").is_none() && shard(&"A".repeat(64)).is_none() && shard(&"g".repeat(64)).is_none()
    );
    assert_eq!(
        tokens("Medusa, MEDUSA! città-stato", 8),
        ["medusa", "città", "stato"]
    );
    assert_eq!(tokens("a b c d e f", 3).len(), 3);
}

#[test]
fn a_hundred_thousand_creations_stay_fast() {
    let mut a = memory();
    let tx_start = std::time::Instant::now();
    for n in 0..100_000_u32 {
        let key = format!("oggetto {} {}", n % 997, n);
        put(&mut a, &key, n, &["forma"], i64::from(n));
    }
    let loaded = tx_start.elapsed();
    let probe = std::time::Instant::now();
    for _ in 0..200 {
        assert!(!a.search("ogget 42", 10).unwrap_or_default().is_empty());
        assert!(a.lookup("oggetto 42 42", 1).ok().flatten().is_some());
    }
    assert!(
        probe.elapsed().as_millis() < 3_000,
        "{loaded:?} {:?}",
        probe.elapsed()
    );
    assert_eq!(a.count().ok(), Some(100_000));
}
