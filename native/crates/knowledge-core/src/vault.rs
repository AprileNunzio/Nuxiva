use std::fs;
use std::io::Write;
use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use nuxiva_context_core::PersonId;

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::seal::{MasterKey, NONCE_LEN};
use crate::store::Partition;

const MAGIC: &[u8; 4] = b"NKG1";
const MAX_FILE: u64 = 256 * 1024 * 1024;

#[derive(Debug)]
pub struct Vault {
    dir: PathBuf,
    key: Arc<MasterKey>,
}

fn aad(owner: &PersonId) -> Vec<u8> {
    format!("nuxiva.knowledge.partition.v1|{}", owner.as_str()).into_bytes()
}

fn io<T>(result: std::io::Result<T>) -> KnowledgeResult<T> {
    result.map_err(|_| KnowledgeError::Io)
}

impl Vault {
    pub fn new(dir: &Path, key: Arc<MasterKey>) -> KnowledgeResult<Self> {
        io(fs::DirBuilder::new()
            .recursive(true)
            .mode(0o700)
            .create(dir))?;
        Ok(Self {
            dir: dir.to_owned(),
            key,
        })
    }

    fn path(&self, owner: &PersonId) -> KnowledgeResult<PathBuf> {
        let name = self.key.file_name(owner.as_str())?;
        Ok(self.dir.join(format!("{name}.nkg")))
    }

    pub fn save(&self, part: &Partition) -> KnowledgeResult<()> {
        let plain =
            zeroize::Zeroizing::new(serde_json::to_vec(part).map_err(|_| KnowledgeError::Corrupt)?);
        let owner_key = self.key.owner(part.owner.as_str())?;
        let (nonce, data) = owner_key.seal(&aad(&part.owner), plain.as_slice())?;
        let mut blob = Vec::with_capacity(
            MAGIC
                .len()
                .saturating_add(nonce.len())
                .saturating_add(data.len()),
        );
        blob.extend_from_slice(MAGIC);
        blob.extend_from_slice(&nonce);
        blob.extend_from_slice(&data);
        let target = self.path(&part.owner)?;
        let temp = target.with_extension("tmp");
        let mut file = io(fs::OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .mode(0o600)
            .open(&temp))?;
        io(file.write_all(&blob))?;
        io(file.sync_all())?;
        io(fs::rename(&temp, &target))
    }

    pub fn load(&self, owner: &PersonId) -> KnowledgeResult<Option<Partition>> {
        let path = self.path(owner)?;
        let meta = match fs::metadata(&path) {
            Ok(meta) => meta,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err(KnowledgeError::Io),
        };
        if meta.len() > MAX_FILE {
            return Err(KnowledgeError::TooLarge);
        }
        let blob = io(fs::read(&path))?;
        let body = blob
            .strip_prefix(MAGIC.as_slice())
            .ok_or(KnowledgeError::Corrupt)?;
        let (nonce, data) = body
            .split_at_checked(NONCE_LEN)
            .ok_or(KnowledgeError::Corrupt)?;
        let plain = self
            .key
            .owner(owner.as_str())?
            .open(&aad(owner), nonce, data)?;
        let mut part: Partition =
            serde_json::from_slice(plain.as_slice()).map_err(|_| KnowledgeError::Corrupt)?;
        if part.owner != *owner {
            return Err(KnowledgeError::Corrupt);
        }
        part.reindex();
        Ok(Some(part))
    }

    pub fn delete(&self, owner: &PersonId) -> KnowledgeResult<bool> {
        let path = self.path(owner)?;
        let len = match fs::metadata(&path) {
            Ok(meta) => meta.len(),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
            Err(_) => return Err(KnowledgeError::Io),
        };
        let mut file = io(fs::OpenOptions::new().write(true).open(&path))?;
        let zeros = vec![0_u8; usize::try_from(len).map_err(|_| KnowledgeError::TooLarge)?];
        io(file.write_all(&zeros))?;
        io(file.sync_all())?;
        io(fs::remove_file(&path))?;
        Ok(true)
    }
}
