#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

use super::*;

#[test]
fn test_key_derivation_determinism() {
    let master = [42u8; KEY_LEN];
    let key1 = derive_day_camera_key(&master, "cam_gate", "2026-11-10").unwrap();
    let key2 = derive_day_camera_key(&master, "cam_gate", "2026-11-10").unwrap();
    assert_eq!(*key1, *key2);

    let key3 = derive_day_camera_key(&master, "cam_backyard", "2026-11-10").unwrap();
    assert_ne!(*key1, *key3);
}

#[test]
fn test_segment_encrypt_and_decrypt_roundtrip() {
    let master = [7u8; KEY_LEN];
    let day_key = derive_day_camera_key(&master, "cam_door", "2026-11-10").unwrap();
    let seg_key = derive_segment_key(&day_key, "seg_001").unwrap();
    let nonce = [1u8; NONCE_LEN];

    let fake_mp4_bytes = vec![0xAB; CHUNK_SIZE * 2 + 1024];

    let encrypted = EncryptedSegment::encrypt_from_raw(RawSegmentInput {
        segment_id: "seg_001".into(),
        camera_id: "cam_door".into(),
        day: "2026-11-10".into(),
        recorded_at: 1_700_000_000,
        duration_ms: 60_000,
        has_audio: true,
        has_video: true,
        tier: RetentionTier::Continuous,
        key: &seg_key,
        base_nonce: nonce,
        raw_media: &fake_mp4_bytes,
    })
    .unwrap();

    assert_eq!(encrypted.meta.chunk_count, 3);
    assert!(encrypted.meta.has_audio);
    assert!(encrypted.meta.has_video);

    let decrypted = encrypted.decrypt_all(&seg_key).unwrap();
    assert_eq!(decrypted, fake_mp4_bytes);
}

#[test]
fn test_streaming_range_decryption() {
    let key = [9u8; KEY_LEN];
    let nonce = [2u8; NONCE_LEN];
    let payload = b"NUXIVA_SECURE_NVR_STREAMING_TEST_PAYLOAD";

    let encrypted = EncryptedSegment::encrypt_from_raw(RawSegmentInput {
        segment_id: "seg_stream".into(),
        camera_id: "cam_01".into(),
        day: "2026-11-10".into(),
        recorded_at: 1_700_000_000,
        duration_ms: 10_000,
        has_audio: true,
        has_video: true,
        tier: RetentionTier::EventClip,
        key: &key,
        base_nonce: nonce,
        raw_media: payload,
    })
    .unwrap();

    let reader = DecryptingStreamReader::new(&encrypted, &key);
    let slice = reader.read_range(7, 13).unwrap();
    assert_eq!(slice, b"SECURE_NVR_ST");
}

#[test]
fn test_retention_policy_expiration() {
    let policy = RetentionPolicy::new(3600, 86400);

    assert!(!policy.is_expired(RetentionTier::Continuous, 1000, 2000));
    assert!(policy.is_expired(RetentionTier::Continuous, 1000, 5000));
    assert!(!policy.is_expired(RetentionTier::EventClip, 1000, 50_000));
    assert!(policy.is_expired(RetentionTier::EventClip, 1000, 100_000));
    assert!(!policy.is_expired(RetentionTier::Pinned, 1000, 999_999_999));
}

#[test]
fn test_corrupted_chunk_fails_authentication() {
    let key = [3u8; KEY_LEN];
    let nonce = [4u8; NONCE_LEN];
    let payload = b"SENSITIVE_MEDIA_RECORDING";

    let mut encrypted = EncryptedSegment::encrypt_from_raw(RawSegmentInput {
        segment_id: "seg_tamper".into(),
        camera_id: "cam_01".into(),
        day: "2026-11-10".into(),
        recorded_at: 1_700_000_000,
        duration_ms: 5000,
        has_audio: true,
        has_video: true,
        tier: RetentionTier::Continuous,
        key: &key,
        base_nonce: nonce,
        raw_media: payload,
    })
    .unwrap();

    if let Some(chunk) = encrypted.chunks.get_mut(0) {
        if let Some(byte) = chunk.get_mut(5) {
            *byte ^= 0xFF;
        }
    }

    let err = encrypted.decrypt_all(&key);
    assert!(err.is_err());
}

#[test]
fn test_serialization_and_chunk_decryption_roundtrip() {
    let key = [5u8; KEY_LEN];
    let nonce = [8u8; NONCE_LEN];
    let payload = b"SERIALIZED_VAULT_MEDIA_TEST_SEGMENT_DATA_STREAM";

    let encrypted = EncryptedSegment::encrypt_from_raw(RawSegmentInput {
        segment_id: "seg_ser".into(),
        camera_id: "cam_gate".into(),
        day: "2026-11-10".into(),
        recorded_at: 1_700_000_000,
        duration_ms: 12_000,
        has_audio: true,
        has_video: true,
        tier: RetentionTier::Pinned,
        key: &key,
        base_nonce: nonce,
        raw_media: payload,
    })
    .unwrap();

    let bytes = encrypted.to_bytes().unwrap();
    let loaded = EncryptedSegment::from_bytes(&bytes).unwrap();
    assert_eq!(loaded.meta.segment_id, "seg_ser");
    assert_eq!(loaded.meta.tier, RetentionTier::Pinned);
    assert_eq!(loaded.chunks.len(), 1);

    let chunk0 = loaded.decrypt_chunk_at(&key, 0).unwrap();
    assert_eq!(chunk0, payload);

    let all = loaded.decrypt_all(&key).unwrap();
    assert_eq!(all, payload);
}
