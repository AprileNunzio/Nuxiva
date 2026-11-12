#![allow(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects
)]

use crate::{ByteRange, parse_range};
use crate::{Catalog, Marker, Policy, Segment, Tier, next_marker, plan, spans};

fn seg(camera: &str, id: &str, start: u64, bytes: u64, tier: Tier) -> Segment {
    Segment {
        id: id.into(),
        camera: camera.into(),
        start_ms: start,
        duration_ms: 60_000,
        bytes,
        tier,
        audio: true,
        video: true,
    }
}

fn filled() -> Catalog {
    let mut c = Catalog::new();
    for i in 0..10u64 {
        c.insert(seg(
            "cam-a",
            &format!("s{i}"),
            i * 60_000,
            100,
            Tier::Continuous,
        ))
        .unwrap();
    }
    c.insert(seg("cam-a", "late", 900_000, 100, Tier::Continuous))
        .unwrap();
    c
}

#[test]
fn range_includes_overlapping_predecessor() {
    let c = filled();
    let got = c.range("cam-a", 90_000, 200_000, 50).unwrap();
    let ids: Vec<&str> = got.iter().map(|s| s.id.as_str()).collect();
    assert_eq!(ids, ["s1", "s2", "s3"]);
    assert!(c.range("../x", 0, 1, 10).is_err());
    assert!(c.range("cam-z", 0, 10, 10).unwrap().is_empty());
}

#[test]
fn seek_inside_and_in_gap() {
    let c = filled();
    let inside = c.seek("cam-a", 125_000).unwrap();
    assert_eq!(inside.segment.id, "s2");
    assert_eq!(inside.offset_ms, 5_000);
    let gap = c.seek("cam-a", 700_000).unwrap();
    assert_eq!(gap.segment.id, "late");
    assert_eq!(gap.gap_ms, 200_000);
    assert!(c.seek("cam-a", 2_000_000).is_none());
    assert_eq!(c.after("cam-a", "s9").unwrap().id, "late");
}

#[test]
fn insert_replaces_same_id_and_same_start() {
    let mut c = filled();
    c.insert(seg("cam-a", "s1", 61_000, 5, Tier::Event))
        .unwrap();
    assert_eq!(c.len(), 11);
    c.insert(seg("cam-a", "dup", 0, 5, Tier::Event)).unwrap();
    assert_eq!(c.len(), 11);
    assert!(c.get("cam-a", "s0").is_none());
    assert!(c.insert(seg("cam a", "x", 0, 1, Tier::Event)).is_err());
    let back = Catalog::from_json(&c.to_json().unwrap()).unwrap();
    assert_eq!(back.len(), c.len());
}

#[test]
fn spans_merge_and_markers_jump() {
    let c = filled();
    let all = c.camera_segments("cam-a");
    let s = spans(&all, 2_000);
    assert_eq!(s.len(), 2);
    assert_eq!(s[0].segments, 10);
    assert_eq!(s[0].end_ms, 600_000);
    let markers = vec![
        Marker {
            at_ms: 100,
            camera: "cam-a".into(),
            kind: "person".into(),
            id: "a".into(),
            label: String::new(),
            score: 0.9,
        },
        Marker {
            at_ms: 500,
            camera: "cam-a".into(),
            kind: "speech".into(),
            id: "b".into(),
            label: String::new(),
            score: 0.9,
        },
        Marker {
            at_ms: 900,
            camera: "cam-a".into(),
            kind: "person".into(),
            id: "c".into(),
            label: String::new(),
            score: 0.9,
        },
    ];
    assert_eq!(next_marker(&markers, 100, true, &[]).unwrap().id, "b");
    assert_eq!(
        next_marker(&markers, 100, true, &["person".into()])
            .unwrap()
            .id,
        "c"
    );
    assert_eq!(next_marker(&markers, 900, false, &[]).unwrap().id, "b");
    assert!(next_marker(&markers, 900, true, &[]).is_none());
}

#[test]
fn retention_promotes_expires_and_evicts() {
    let mut c = filled();
    c.set_tier("cam-a", "s0", Tier::Pinned).unwrap();
    let policy = Policy {
        continuous_ms: 400_000,
        event_ms: 10_000_000,
        quota_bytes: 0,
        event_pad_ms: 5_000,
        continuous_overrides: std::collections::BTreeMap::new(),
    };
    let events = vec![("cam-a".to_owned(), 130_000u64)];
    let p = plan(&c, &policy, &events, 1_000_000);
    assert!(p.promote.contains(&("cam-a".into(), "s2".into())));
    assert!(p.expire.contains(&("cam-a".into(), "s3".into())));
    assert!(!p.expire.iter().any(|(_, id)| id == "s0" || id == "s2"));
    let mut longer = policy.clone();
    longer
        .continuous_overrides
        .insert("cam-a".into(), 10_000_000);
    assert!(plan(&c, &longer, &events, 1_000_000).expire.is_empty());
    let tight = Policy {
        quota_bytes: 250,
        ..policy
    };
    let q = plan(&c, &tight, &events, 1_000_000);
    assert!(q.kept_bytes <= 250);
    assert!(!q.evict.iter().any(|(_, id)| id == "s0"));
    assert_eq!(q.evict.first().unwrap().1, "s9");
}

#[test]
fn byte_ranges() {
    assert_eq!(parse_range("", 100), ByteRange::Whole);
    assert_eq!(
        parse_range("bytes=0-9", 100),
        ByteRange::Part { start: 0, end: 9 }
    );
    assert_eq!(
        parse_range("bytes=90-", 100),
        ByteRange::Part { start: 90, end: 99 }
    );
    assert_eq!(
        parse_range("bytes=-10", 100),
        ByteRange::Part { start: 90, end: 99 }
    );
    assert_eq!(
        parse_range("bytes=-1000", 100),
        ByteRange::Part { start: 0, end: 99 }
    );
    assert_eq!(
        parse_range("bytes=50-5000", 100),
        ByteRange::Part { start: 50, end: 99 }
    );
    for bad in [
        "bytes=100-",
        "bytes=9-1",
        "bytes=0-1,4-5",
        "items=0-1",
        "bytes=-0",
        "bytes=a-b",
        "bytes=+1-2",
    ] {
        assert_eq!(parse_range(bad, 100), ByteRange::Unsatisfiable, "{bad}");
    }
    assert_eq!(parse_range("bytes=0-1", 0), ByteRange::Unsatisfiable);
}
