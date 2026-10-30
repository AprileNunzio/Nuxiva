use std::fs::{self, DirBuilder, OpenOptions};
use std::io::{Read, Write};
use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Nonce};
use hkdf::Hkdf;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use zeroize::{Zeroize, ZeroizeOnDrop, Zeroizing};

const MAGIC: &[u8; 4] = b"NXS1";
const KEY_FILE: &str = "vault.key";
const IDENTITY_FILE: &str = "identity.bin";
const INFO: &[u8] = b"nuxiva-satellite/identity/v1";
const NONCE_LEN: usize = 12;
const MAX_FILE: u64 = 256 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Zeroize, ZeroizeOnDrop)]
pub struct Identity {
    pub server: String,
    pub node_id: String,
    pub name: String,
    pub token: String,
    pub ca_pem: String,
}

#[derive(Debug, PartialEq, Eq)]
pub enum VaultError {
    Io(String),
    Corrupted,
    Insecure(PathBuf),
}

impl std::fmt::Display for VaultError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(message) => write!(f, "vault_io: {message}"),
            Self::Corrupted => write!(f, "vault_corrupted"),
            Self::Insecure(path) => write!(f, "vault_insecure_permissions: {}", path.display()),
        }
    }
}

#[derive(Debug)]
pub struct Vault {
    dir: PathBuf,
    binding: Vec<u8>,
}

impl Vault {
    pub fn new(dir: impl Into<PathBuf>, machine_id: Option<&str>) -> Self {
        Self {
            dir: dir.into(),
            binding: machine_id.unwrap_or_default().trim().as_bytes().to_vec(),
        }
    }

    #[must_use]
    pub fn exists(&self) -> bool {
        self.dir.join(IDENTITY_FILE).is_file()
    }

    pub fn save(&self, identity: &Identity) -> Result<(), VaultError> {
        self.ensure_dir()?;
        let cipher = self.cipher(true)?;
        let plain = Zeroizing::new(
            serde_json::to_vec(identity).map_err(|e| VaultError::Io(e.to_string()))?,
        );
        let mut nonce = [0u8; NONCE_LEN];
        getrandom::fill(&mut nonce).map_err(|e| VaultError::Io(e.to_string()))?;
        let sealed = cipher
            .encrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: &plain,
                    aad: MAGIC,
                },
            )
            .map_err(|_| VaultError::Corrupted)?;
        let mut blob = Vec::with_capacity(
            MAGIC
                .len()
                .saturating_add(NONCE_LEN)
                .saturating_add(sealed.len()),
        );
        blob.extend_from_slice(MAGIC);
        blob.extend_from_slice(&nonce);
        blob.extend_from_slice(&sealed);
        write_atomic(&self.dir.join(IDENTITY_FILE), &blob)
    }

    pub fn load(&self) -> Result<Identity, VaultError> {
        let path = self.dir.join(IDENTITY_FILE);
        check_private(&path)?;
        let blob = read_limited(&path)?;
        let body = blob
            .strip_prefix(MAGIC.as_slice())
            .ok_or(VaultError::Corrupted)?;
        let (nonce, sealed) = body
            .split_at_checked(NONCE_LEN)
            .ok_or(VaultError::Corrupted)?;
        let plain = Zeroizing::new(
            self.cipher(false)?
                .decrypt(
                    Nonce::from_slice(nonce),
                    Payload {
                        msg: sealed,
                        aad: MAGIC,
                    },
                )
                .map_err(|_| VaultError::Corrupted)?,
        );
        serde_json::from_slice(&plain).map_err(|_| VaultError::Corrupted)
    }

    pub fn destroy(&self) -> Result<(), VaultError> {
        for name in [IDENTITY_FILE, KEY_FILE] {
            let path = self.dir.join(name);
            if path.exists() {
                shred(&path)?;
            }
        }
        Ok(())
    }

    fn ensure_dir(&self) -> Result<(), VaultError> {
        DirBuilder::new()
            .recursive(true)
            .mode(0o700)
            .create(&self.dir)
            .map_err(|e| VaultError::Io(e.to_string()))
    }

    fn cipher(&self, create: bool) -> Result<Aes256Gcm, VaultError> {
        let master = self.master_key(create)?;
        let mut derived = Zeroizing::new([0u8; 32]);
        Hkdf::<Sha256>::new(Some(&self.binding), master.as_slice())
            .expand(INFO, derived.as_mut_slice())
            .map_err(|_| VaultError::Corrupted)?;
        Aes256Gcm::new_from_slice(derived.as_slice()).map_err(|_| VaultError::Corrupted)
    }

    fn master_key(&self, create: bool) -> Result<Zeroizing<Vec<u8>>, VaultError> {
        let path = self.dir.join(KEY_FILE);
        if path.exists() {
            check_private(&path)?;
            let key = Zeroizing::new(read_limited(&path)?);
            return if key.len() == 32 {
                Ok(key)
            } else {
                Err(VaultError::Corrupted)
            };
        }
        if !create {
            return Err(VaultError::Corrupted);
        }
        let mut key = Zeroizing::new(vec![0u8; 32]);
        getrandom::fill(key.as_mut_slice()).map_err(|e| VaultError::Io(e.to_string()))?;
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&path)
            .map_err(|e| VaultError::Io(e.to_string()))?;
        file.write_all(&key)
            .and_then(|()| file.sync_all())
            .map_err(|e| VaultError::Io(e.to_string()))?;
        Ok(key)
    }
}

fn check_private(path: &Path) -> Result<(), VaultError> {
    let meta = fs::symlink_metadata(path).map_err(|e| VaultError::Io(e.to_string()))?;
    if !meta.is_file() || meta.permissions().mode() & 0o077 != 0 {
        return Err(VaultError::Insecure(path.to_path_buf()));
    }
    Ok(())
}

fn read_limited(path: &Path) -> Result<Vec<u8>, VaultError> {
    let mut data = Vec::new();
    fs::File::open(path)
        .and_then(|file| file.take(MAX_FILE).read_to_end(&mut data))
        .map_err(|e| VaultError::Io(e.to_string()))?;
    Ok(data)
}

pub fn write_atomic(path: &Path, data: &[u8]) -> Result<(), VaultError> {
    let tmp = path.with_extension("tmp");
    let mut file = OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .mode(0o600)
        .open(&tmp)
        .map_err(|e| VaultError::Io(e.to_string()))?;
    file.write_all(data)
        .and_then(|()| file.sync_all())
        .and_then(|()| fs::rename(&tmp, path))
        .map_err(|e| VaultError::Io(e.to_string()))
}

pub fn shred(path: &Path) -> Result<(), VaultError> {
    let size = fs::metadata(path)
        .map_err(|e| VaultError::Io(e.to_string()))?
        .len();
    let mut file = OpenOptions::new()
        .write(true)
        .open(path)
        .map_err(|e| VaultError::Io(e.to_string()))?;
    let zeros = vec![0u8; usize::try_from(size.min(MAX_FILE)).unwrap_or(0)];
    file.write_all(&zeros)
        .and_then(|()| file.sync_all())
        .and_then(|()| fs::remove_file(path))
        .map_err(|e| VaultError::Io(e.to_string()))
}
