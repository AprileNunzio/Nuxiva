use std::fs;
use std::path::Path;

use crate::error::CollaudoError;

fn digest(token: &str) -> blake3::Hash {
    blake3::keyed_hash(&[0x6e; 32], token.as_bytes())
}

pub fn generate() -> Result<String, CollaudoError> {
    let mut raw = [0u8; 32];
    getrandom::fill(&mut raw).map_err(|_| CollaudoError::Random)?;
    Ok(blake3::Hash::from_bytes(raw).to_hex().to_string())
}

pub fn random_key() -> Result<[u8; 32], CollaudoError> {
    let mut raw = [0u8; 32];
    getrandom::fill(&mut raw).map_err(|_| CollaudoError::Random)?;
    Ok(raw)
}

pub fn random_id() -> Result<String, CollaudoError> {
    let hex = random_key().map(|raw| blake3::Hash::from_bytes(raw).to_hex())?;
    Ok(hex.as_str().get(..16).unwrap_or_default().to_owned())
}

#[derive(Debug)]
pub struct TokenVault<'a> {
    path: &'a Path,
}

impl<'a> TokenVault<'a> {
    #[must_use]
    pub fn at(path: &'a Path) -> Self {
        Self { path }
    }

    pub fn issue(&self) -> Result<String, CollaudoError> {
        let token = generate()?;
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent)?;
        }
        let tmp = self.path.with_extension("tmp");
        fs::write(&tmp, digest(&token).to_hex().as_bytes())?;
        restrict(&tmp)?;
        fs::rename(&tmp, self.path)?;
        Ok(token)
    }

    pub fn revoke(&self) -> Result<(), CollaudoError> {
        match fs::remove_file(self.path) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(e.into()),
        }
    }

    #[must_use]
    pub fn verify(&self, presented: &str) -> bool {
        if presented.len() != 64 || !presented.bytes().all(|b| b.is_ascii_hexdigit()) {
            return false;
        }
        let Ok(stored) = fs::read_to_string(self.path) else {
            return false;
        };
        let Ok(stored) = blake3::Hash::from_hex(stored.trim()) else {
            return false;
        };
        digest(&presented.to_ascii_lowercase()) == stored
    }
}

#[cfg(unix)]
fn restrict(path: &Path) -> Result<(), CollaudoError> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
    Ok(())
}

#[cfg(not(unix))]
fn restrict(_path: &Path) -> Result<(), CollaudoError> {
    Ok(())
}
