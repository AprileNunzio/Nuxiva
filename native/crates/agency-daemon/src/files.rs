use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;

use crate::error::AgencyError;

const MAX_FILE: u64 = 64 * 1024 * 1024;

fn nofollow() -> i32 {
    i32::try_from(rustix::fs::OFlags::NOFOLLOW.bits()).unwrap_or(0)
}

pub fn private_dir(path: &Path) -> Result<(), AgencyError> {
    use std::os::unix::fs::{DirBuilderExt, PermissionsExt};
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(path)?;
    let meta = fs::symlink_metadata(path)?;
    if !meta.is_dir() {
        return Err(AgencyError::Config("state path is not a directory"));
    }
    fs::set_permissions(path, fs::Permissions::from_mode(0o700))?;
    Ok(())
}

pub fn read(path: &Path) -> Result<Option<Vec<u8>>, AgencyError> {
    use std::os::unix::fs::OpenOptionsExt;
    let file = match OpenOptions::new()
        .read(true)
        .custom_flags(nofollow())
        .open(path)
    {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error.into()),
    };
    let mut bytes = Vec::new();
    file.take(MAX_FILE).read_to_end(&mut bytes)?;
    Ok(Some(bytes))
}

pub fn write_atomic(path: &Path, bytes: &[u8]) -> Result<(), AgencyError> {
    use std::os::unix::fs::OpenOptionsExt;
    let parent = path
        .parent()
        .ok_or(AgencyError::Config("file without parent"))?;
    let mut nonce = [0u8; 8];
    getrandom::fill(&mut nonce).map_err(|e| std::io::Error::other(e.to_string()))?;
    let tmp = parent.join(format!(".tmp-{:016x}", u64::from_le_bytes(nonce)));
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .custom_flags(nofollow())
            .open(&tmp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        fs::rename(&tmp, path)?;
        File::open(parent)?.sync_all()
    })();
    if result.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    result.map_err(AgencyError::from)
}

pub fn load_key(path: &Path) -> Result<[u8; 32], AgencyError> {
    if let Some(bytes) = read(path)? {
        return <[u8; 32]>::try_from(bytes.as_slice())
            .map_err(|_| AgencyError::Config("ledger key must be 32 bytes"));
    }
    let mut key = [0u8; 32];
    getrandom::fill(&mut key).map_err(|e| std::io::Error::other(e.to_string()))?;
    write_atomic(path, &key)?;
    Ok(key)
}
