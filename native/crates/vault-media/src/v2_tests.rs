#![allow(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::cast_possible_truncation
)]

use crate::v2::{
    FRAME_LEN, SegmentSpec, chunk_span, open_blob, open_chunk, open_segment, parse_header,
    seal_blob, seal_segment,
};
use crate::{CHUNK_SIZE, NONCE_LEN};

fn spec() -> SegmentSpec<'static> {
    SegmentSpec {
        segment_id: "seg_20261112_101500",
        camera_id: "cam-door",
        day: "2026-11-12",
        recorded_at_ms: 1_794_478_500_000,
        duration_ms: 60_000,
        has_audio: true,
        has_video: true,
        tier: "continuous",
    }
}

#[test]
fn roundtrip_and_random_access() {
    let master = [9u8; 32];
    let nonce = [3u8; NONCE_LEN];
    let media: Vec<u8> = (0..CHUNK_SIZE * 2 + 777).map(|i| (i % 251) as u8).collect();
    let sealed = seal_segment(&master, &spec(), &nonce, &media).unwrap();
    let (header, plain) = open_segment(&master, &sealed).unwrap();
    assert_eq!(plain, media);
    assert_eq!(header.chunk_count, 3);
    let opened = parse_header(&sealed).unwrap();
    let off = usize::try_from(opened.frame_offset(2)).unwrap();
    let chunk = open_chunk(&master, &opened, 2, &sealed[off..off + opened.frame_len(2)]).unwrap();
    assert_eq!(chunk, media[CHUNK_SIZE * 2..]);
    assert_eq!(
        opened.frame_offset(1) - opened.frame_offset(0),
        FRAME_LEN as u64
    );
}

#[test]
fn tampering_is_detected() {
    let master = [9u8; 32];
    let nonce = [4u8; NONCE_LEN];
    let media = vec![7u8; CHUNK_SIZE + 10];
    let sealed = seal_segment(&master, &spec(), &nonce, &media).unwrap();
    let text = String::from_utf8_lossy(&sealed).to_string();
    let pos = text.find("continuous").unwrap();
    let mut forged = sealed.clone();
    forged[pos..pos + 5].copy_from_slice(b"pinne");
    forged.splice(pos + 5..pos + 10, b"d".iter().copied());
    assert!(open_segment(&master, &forged).is_err());
    let mut truncated = sealed.clone();
    truncated.truncate(sealed.len() - 20);
    assert!(open_segment(&master, &truncated).is_err());
    let mut flipped = sealed.clone();
    let last = flipped.len() - 1;
    flipped[last] ^= 1;
    assert!(open_segment(&master, &flipped).is_err());
    assert!(open_segment(&[1u8; 32], &sealed).is_err());
}

#[test]
fn rejects_hostile_ids_and_empty_media() {
    let master = [1u8; 32];
    let nonce = [0u8; NONCE_LEN];
    let mut bad = spec();
    bad.camera_id = "../etc";
    assert!(seal_segment(&master, &bad, &nonce, b"x").is_err());
    let sealed = seal_segment(&master, &spec(), &nonce, b"").unwrap();
    let (header, plain) = open_segment(&master, &sealed).unwrap();
    assert_eq!(header.chunk_count, 1);
    assert!(plain.is_empty());
}

#[test]
fn chunk_span_bounds() {
    let size = CHUNK_SIZE as u64;
    assert_eq!(chunk_span(size * 3, 0, 10), Some((0, 0)));
    assert_eq!(chunk_span(size * 3, size - 1, size), Some((0, 1)));
    assert_eq!(chunk_span(size * 3, 5, u64::MAX), Some((0, 2)));
    assert_eq!(chunk_span(size, size, size + 4), None);
    assert_eq!(chunk_span(0, 0, 0), None);
}

#[test]
fn blob_roundtrip_binds_context() {
    let master = [5u8; 32];
    let nonce = [8u8; NONCE_LEN];
    let blob = seal_blob(&master, "nvr.catalog|cam-door", &nonce, b"{\"a\":1}").unwrap();
    assert_eq!(
        open_blob(&master, "nvr.catalog|cam-door", &blob).unwrap(),
        b"{\"a\":1}"
    );
    assert!(open_blob(&master, "nvr.catalog|cam-gate", &blob).is_err());
}
