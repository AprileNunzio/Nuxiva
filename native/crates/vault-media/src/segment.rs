use serde::{Deserialize, Serialize};

use crate::crypto::{CHUNK_SIZE, KEY_LEN, NONCE_LEN, decrypt_chunk, encrypt_chunk};
use crate::error::{MediaVaultError, MediaVaultResult};
use crate::retention::RetentionTier;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SegmentMeta {
    pub segment_id: String,
    pub camera_id: String,
    pub day: String,
    pub recorded_at: u64,
    pub duration_ms: u32,
    pub has_audio: bool,
    pub has_video: bool,
    pub tier: RetentionTier,
    pub total_plaintext_bytes: u64,
    pub chunk_count: u32,
    pub blake3_digest: [u8; 32],
    pub base_nonce: [u8; NONCE_LEN],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawSegmentInput<'a> {
    pub segment_id: String,
    pub camera_id: String,
    pub day: String,
    pub recorded_at: u64,
    pub duration_ms: u32,
    pub has_audio: bool,
    pub has_video: bool,
    pub tier: RetentionTier,
    pub key: &'a [u8; KEY_LEN],
    pub base_nonce: [u8; NONCE_LEN],
    pub raw_media: &'a [u8],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EncryptedSegment {
    pub meta: SegmentMeta,
    pub chunks: Vec<Vec<u8>>,
}

impl EncryptedSegment {
    pub fn encrypt_from_raw(input: RawSegmentInput<'_>) -> MediaVaultResult<Self> {
        let hash = blake3::hash(input.raw_media);
        let blake3_digest = *hash.as_bytes();

        let mut chunks = Vec::new();
        let mut idx: u64 = 0;

        for chunk_slice in input.raw_media.chunks(CHUNK_SIZE) {
            let encrypted = encrypt_chunk(input.key, &input.base_nonce, idx, chunk_slice)?;
            chunks.push(encrypted);
            idx = idx.saturating_add(1);
        }

        let chunk_count = u32::try_from(chunks.len())
            .map_err(|_| MediaVaultError::Serialization("chunk count overflow".into()))?;

        let meta = SegmentMeta {
            segment_id: input.segment_id,
            camera_id: input.camera_id,
            day: input.day,
            recorded_at: input.recorded_at,
            duration_ms: input.duration_ms,
            has_audio: input.has_audio,
            has_video: input.has_video,
            tier: input.tier,
            total_plaintext_bytes: input.raw_media.len() as u64,
            chunk_count,
            blake3_digest,
            base_nonce: input.base_nonce,
        };

        Ok(Self { meta, chunks })
    }

    pub fn to_bytes(&self) -> MediaVaultResult<Vec<u8>> {
        let meta_bytes = serde_json::to_vec(&self.meta)
            .map_err(|e| MediaVaultError::Serialization(e.to_string()))?;
        let meta_len = u32::try_from(meta_bytes.len())
            .map_err(|_| MediaVaultError::Serialization("meta too large".into()))?;
        let cap = 8usize.saturating_add(meta_bytes.len()).saturating_add(
            self.chunks
                .len()
                .saturating_mul(CHUNK_SIZE.saturating_add(32)),
        );
        let mut out = Vec::with_capacity(cap);
        out.extend_from_slice(b"NVM1");
        out.extend_from_slice(&meta_len.to_be_bytes());
        out.extend_from_slice(&meta_bytes);
        for chunk in &self.chunks {
            let clen = u32::try_from(chunk.len())
                .map_err(|_| MediaVaultError::Serialization("chunk too large".into()))?;
            out.extend_from_slice(&clen.to_be_bytes());
            out.extend_from_slice(chunk);
        }
        Ok(out)
    }

    pub fn from_bytes(bytes: &[u8]) -> MediaVaultResult<Self> {
        if bytes.len() < 8 {
            return Err(MediaVaultError::CorruptedPayload);
        }
        let magic = bytes.get(..4).ok_or(MediaVaultError::CorruptedPayload)?;
        if magic != b"NVM1" {
            return Err(MediaVaultError::CorruptedPayload);
        }
        let len_slice = bytes.get(4..8).ok_or(MediaVaultError::CorruptedPayload)?;
        let mut len_arr = [0u8; 4];
        len_arr.copy_from_slice(len_slice);
        let meta_len = u32::from_be_bytes(len_arr) as usize;
        let meta_end = 8usize.saturating_add(meta_len);
        let meta_slice = bytes
            .get(8..meta_end)
            .ok_or(MediaVaultError::CorruptedPayload)?;
        let meta: SegmentMeta = serde_json::from_slice(meta_slice)
            .map_err(|e| MediaVaultError::Serialization(e.to_string()))?;
        let mut offset = 8usize.saturating_add(meta_len);
        let mut chunks = Vec::with_capacity(meta.chunk_count as usize);
        while offset < bytes.len() {
            let next_offset = offset.saturating_add(4);
            let clen_slice = bytes
                .get(offset..next_offset)
                .ok_or(MediaVaultError::CorruptedPayload)?;
            let mut clen_arr = [0u8; 4];
            clen_arr.copy_from_slice(clen_slice);
            let clen = u32::from_be_bytes(clen_arr) as usize;
            offset = next_offset;
            let chunk_end = offset.saturating_add(clen);
            let chunk_data = bytes
                .get(offset..chunk_end)
                .ok_or(MediaVaultError::CorruptedPayload)?;
            chunks.push(chunk_data.to_vec());
            offset = chunk_end;
        }
        Ok(Self { meta, chunks })
    }

    pub fn decrypt_chunk_at(&self, key: &[u8; KEY_LEN], index: usize) -> MediaVaultResult<Vec<u8>> {
        let chunk = self
            .chunks
            .get(index)
            .ok_or(MediaVaultError::InvalidRange)?;
        decrypt_chunk(key, &self.meta.base_nonce, index as u64, chunk)
    }

    pub fn decrypt_all(&self, key: &[u8; KEY_LEN]) -> MediaVaultResult<Vec<u8>> {
        let mut out = Vec::with_capacity(self.meta.total_plaintext_bytes as usize);
        for (idx, chunk) in self.chunks.iter().enumerate() {
            let decrypted = decrypt_chunk(key, &self.meta.base_nonce, idx as u64, chunk)?;
            out.extend_from_slice(&decrypted);
        }

        let computed_hash = blake3::hash(&out);
        if *computed_hash.as_bytes() != self.meta.blake3_digest {
            return Err(MediaVaultError::ChunkCorrupted);
        }

        Ok(out)
    }
}
