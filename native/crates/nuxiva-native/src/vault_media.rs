use nuxiva_vault_media::{
    EncryptedSegment, KEY_LEN, NONCE_LEN, RawSegmentInput, RetentionPolicy, RetentionTier,
    derive_day_camera_key, derive_segment_key,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use zeroize::Zeroizing;

#[pyclass]
#[derive(Debug)]
pub struct RustMediaVault {
    master_key: Zeroizing<[u8; KEY_LEN]>,
    policy: RetentionPolicy,
}

#[pymethods]
impl RustMediaVault {
    #[new]
    #[pyo3(signature = (master_key, continuous_seconds=7200, event_seconds=604_800))]
    pub fn new(master_key: &[u8], continuous_seconds: u64, event_seconds: u64) -> PyResult<Self> {
        if master_key.len() < KEY_LEN {
            return Err(PyValueError::new_err(
                "master key must be at least 32 bytes",
            ));
        }
        let mut key = Zeroizing::new([0u8; KEY_LEN]);
        if let Some(src) = master_key.get(..KEY_LEN) {
            key.copy_from_slice(src);
        }
        Ok(Self {
            master_key: key,
            policy: RetentionPolicy::new(continuous_seconds, event_seconds),
        })
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (camera_id, day, segment_id, recorded_at, duration_ms, has_audio, has_video, tier_str, nonce_bytes, raw_media))]
    pub fn encrypt_segment(
        &self,
        camera_id: &str,
        day: &str,
        segment_id: &str,
        recorded_at: u64,
        duration_ms: u32,
        has_audio: bool,
        has_video: bool,
        tier_str: &str,
        nonce_bytes: &[u8],
        raw_media: &[u8],
    ) -> PyResult<Vec<u8>> {
        let day_key = derive_day_camera_key(self.master_key.as_slice(), camera_id, day)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let seg_key = derive_segment_key(&day_key, segment_id)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;

        let mut base_nonce = [0u8; NONCE_LEN];
        if nonce_bytes.len() >= NONCE_LEN {
            if let Some(src) = nonce_bytes.get(..NONCE_LEN) {
                base_nonce.copy_from_slice(src);
            }
        }

        let tier = match tier_str.to_lowercase().as_str() {
            "pinned" => RetentionTier::Pinned,
            "event" | "event_clip" => RetentionTier::EventClip,
            _ => RetentionTier::Continuous,
        };

        let input = RawSegmentInput {
            segment_id: segment_id.into(),
            camera_id: camera_id.into(),
            day: day.into(),
            recorded_at,
            duration_ms,
            has_audio,
            has_video,
            tier,
            key: &seg_key,
            base_nonce,
            raw_media,
        };

        let encrypted = EncryptedSegment::encrypt_from_raw(input)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;

        encrypted
            .to_bytes()
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    pub fn decrypt_segment(
        &self,
        py: Python<'_>,
        camera_id: &str,
        day: &str,
        segment_id: &str,
        encrypted_bytes: &[u8],
    ) -> PyResult<Py<PyBytes>> {
        let day_key = derive_day_camera_key(self.master_key.as_slice(), camera_id, day)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let seg_key = derive_segment_key(&day_key, segment_id)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let segment = EncryptedSegment::from_bytes(encrypted_bytes)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let decrypted = segment
            .decrypt_all(&seg_key)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(PyBytes::new(py, &decrypted).into())
    }

    pub fn decrypt_chunk(
        &self,
        py: Python<'_>,
        camera_id: &str,
        day: &str,
        segment_id: &str,
        encrypted_bytes: &[u8],
        chunk_index: usize,
    ) -> PyResult<Option<Py<PyBytes>>> {
        let day_key = derive_day_camera_key(self.master_key.as_slice(), camera_id, day)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let seg_key = derive_segment_key(&day_key, segment_id)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let segment = EncryptedSegment::from_bytes(encrypted_bytes)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        if chunk_index >= segment.chunks.len() {
            return Ok(None);
        }
        let decrypted = segment
            .decrypt_chunk_at(&seg_key, chunk_index)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(Some(PyBytes::new(py, &decrypted).into()))
    }

    #[allow(clippy::unused_self)]
    pub fn get_meta(&self, encrypted_bytes: &[u8]) -> PyResult<String> {
        let segment = EncryptedSegment::from_bytes(encrypted_bytes)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        serde_json::to_string(&segment.meta).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    pub fn is_expired(&self, tier_str: &str, recorded_at: u64, now: u64) -> bool {
        let tier = match tier_str.to_lowercase().as_str() {
            "pinned" => RetentionTier::Pinned,
            "event" | "event_clip" => RetentionTier::EventClip,
            _ => RetentionTier::Continuous,
        };
        self.policy.is_expired(tier, recorded_at, now)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMediaVault>()?;
    Ok(())
}
