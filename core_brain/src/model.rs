use std::path::{Path, PathBuf};
use std::time::Duration;

use reqwest::redirect::Policy;
use sha2::{Digest, Sha256};
use tokio::fs;
use tokio::io::AsyncWriteExt;

use crate::error::{BrainError, BrainResult};

pub const SPEAKER_MODEL: ModelSpec = ModelSpec {
    file: "wespeaker_en_voxceleb_resnet34_LM.onnx",
    url: "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx",
    sha256: "e9848563da86f263117134dfd7ad63c92355b37de492b55e325400c9d9c39012",
    bytes: 26_530_550,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ModelSpec {
    pub file: &'static str,
    pub url: &'static str,
    pub sha256: &'static str,
    pub bytes: u64,
}

fn hex(bytes: &[u8]) -> String {
    const TABLE: &[u8; 16] = b"0123456789abcdef";
    bytes
        .iter()
        .flat_map(|b| [b >> 4, b & 0x0f])
        .filter_map(|n| TABLE.get(usize::from(n)).copied())
        .map(char::from)
        .collect()
}

#[must_use]
pub fn digest_hex(data: &[u8]) -> String {
    hex(&Sha256::digest(data))
}

impl ModelSpec {
    #[must_use]
    pub fn path_in(&self, dir: &Path) -> PathBuf {
        dir.join(self.file)
    }

    pub fn verify(&self, data: &[u8]) -> BrainResult<()> {
        if u64::try_from(data.len()).ok() != Some(self.bytes) {
            return Err(BrainError::Embedding("model_size"));
        }
        if digest_hex(data) != self.sha256 {
            return Err(BrainError::Embedding("model_hash"));
        }
        Ok(())
    }

    pub async fn load(&self, dir: &Path) -> BrainResult<Vec<u8>> {
        let path = self.path_in(dir);
        let data = fs::read(&path)
            .await
            .map_err(|_| BrainError::Embedding("model_missing"))?;
        self.verify(&data)?;
        Ok(data)
    }

    pub async fn fetch(&self, dir: &Path) -> BrainResult<Vec<u8>> {
        if let Ok(data) = self.load(dir).await {
            return Ok(data);
        }
        if !self.url.starts_with("https://") {
            return Err(BrainError::Embedding("model_url"));
        }
        let client = reqwest::Client::builder()
            .redirect(Policy::limited(5))
            .https_only(true)
            .timeout(Duration::from_mins(10))
            .build()
            .map_err(|_| BrainError::Embedding("model_client"))?;
        let mut response = client
            .get(self.url)
            .send()
            .await
            .and_then(reqwest::Response::error_for_status)
            .map_err(|_| BrainError::Embedding("model_download"))?;
        let mut data = Vec::new();
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|_| BrainError::Embedding("model_download"))?
        {
            let total = u64::try_from(data.len().saturating_add(chunk.len())).unwrap_or(u64::MAX);
            if total > self.bytes {
                return Err(BrainError::Embedding("model_size"));
            }
            data.extend_from_slice(&chunk);
        }
        self.verify(&data)?;
        self.store(dir, &data).await?;
        Ok(data)
    }

    async fn store(&self, dir: &Path, data: &[u8]) -> BrainResult<()> {
        fs::create_dir_all(dir)
            .await
            .map_err(|_| BrainError::Embedding("model_store"))?;
        let target = self.path_in(dir);
        let temp = dir.join(format!("{}.part", self.file));
        let mut file = fs::File::create(&temp)
            .await
            .map_err(|_| BrainError::Embedding("model_store"))?;
        file.write_all(data)
            .await
            .map_err(|_| BrainError::Embedding("model_store"))?;
        file.sync_all()
            .await
            .map_err(|_| BrainError::Embedding("model_store"))?;
        drop(file);
        fs::rename(&temp, &target)
            .await
            .map_err(|_| BrainError::Embedding("model_store"))
    }
}
