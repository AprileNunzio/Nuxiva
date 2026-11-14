use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use crate::error::{BenchError, BenchResult};

pub const MAX_FILE_BYTES: u64 = 64 * 1024 * 1024;

pub fn read_limited(path: &Path) -> BenchResult<Vec<u8>> {
    let file = File::open(path)?;
    let mut bytes = Vec::new();
    file.take(MAX_FILE_BYTES.saturating_add(1))
        .read_to_end(&mut bytes)?;
    if u64::try_from(bytes.len()).unwrap_or(u64::MAX) > MAX_FILE_BYTES {
        return Err(BenchError::TooLarge("file"));
    }
    Ok(bytes)
}

fn sibling(path: &Path) -> BenchResult<PathBuf> {
    let name = path
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or(BenchError::Invalid("path"))?;
    Ok(path.with_file_name(format!(".{name}.{}.tmp", std::process::id())))
}

pub fn write_atomic(path: &Path, bytes: &[u8]) -> BenchResult<()> {
    let tmp = sibling(path)?;
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let outcome = options.open(&tmp).and_then(|mut file| {
        file.write_all(bytes)?;
        file.sync_all()
    });
    if let Err(error) = outcome {
        let _ = fs::remove_file(&tmp);
        return Err(error.into());
    }
    if let Err(error) = fs::rename(&tmp, path) {
        let _ = fs::remove_file(&tmp);
        return Err(error.into());
    }
    Ok(())
}
