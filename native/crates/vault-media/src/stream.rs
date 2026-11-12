use crate::crypto::{KEY_LEN, decrypt_chunk};
use crate::error::MediaVaultResult;
use crate::segment::EncryptedSegment;

#[derive(Debug)]
pub struct DecryptingStreamReader<'a> {
    segment: &'a EncryptedSegment,
    key: &'a [u8; KEY_LEN],
    current_chunk_idx: usize,
}

impl<'a> DecryptingStreamReader<'a> {
    #[must_use]
    pub const fn new(segment: &'a EncryptedSegment, key: &'a [u8; KEY_LEN]) -> Self {
        Self {
            segment,
            key,
            current_chunk_idx: 0,
        }
    }

    pub fn read_range(&self, start: u64, length: usize) -> MediaVaultResult<Vec<u8>> {
        let full = self.segment.decrypt_all(self.key)?;
        let start_pos = start as usize;
        if start_pos >= full.len() {
            return Ok(Vec::new());
        }
        let end_pos = (start_pos.saturating_add(length)).min(full.len());
        Ok(full
            .get(start_pos..end_pos)
            .map_or_else(Vec::new, <[u8]>::to_vec))
    }

    pub fn next_chunk(&mut self) -> MediaVaultResult<Option<Vec<u8>>> {
        if self.current_chunk_idx >= self.segment.chunks.len() {
            return Ok(None);
        }
        let Some(chunk_slice) = self.segment.chunks.get(self.current_chunk_idx) else {
            return Ok(None);
        };
        let decrypted = decrypt_chunk(
            self.key,
            &self.segment.meta.base_nonce,
            self.current_chunk_idx as u64,
            chunk_slice,
        )?;
        self.current_chunk_idx = self.current_chunk_idx.saturating_add(1);
        Ok(Some(decrypted))
    }
}
