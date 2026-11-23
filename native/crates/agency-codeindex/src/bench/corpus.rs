use std::fs;
use std::path::Path;

use super::config::BenchConfig;
use super::error::BenchError;

const DIRS_PER_LEVEL: usize = 1000;

fn mix(value: u64) -> u64 {
    let mut z = value.wrapping_add(0x9E37_79B9_7F4A_7C15);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

#[must_use]
pub fn relative_path(config: &BenchConfig, index: usize) -> String {
    let dir = index.checked_div(config.files_per_dir).unwrap_or(0);
    let major = dir.checked_div(DIRS_PER_LEVEL).unwrap_or(0);
    let minor = dir.checked_rem(DIRS_PER_LEVEL).unwrap_or(0);
    format!("pkg{major:04}/mod{minor:04}/item{index:08}.rs")
}

#[must_use]
pub fn body(config: &BenchConfig, index: usize, revision: usize) -> String {
    let hash = mix(config.seed ^ u64::try_from(index).unwrap_or(u64::MAX));
    let padding = "x".repeat(revision);
    format!(
        "pub fn query_target_{index}() -> u64 {{ {hash} }}\npub const PAD: &str = \"{padding}\";\n"
    )
}

pub fn write_file(
    root: &Path,
    config: &BenchConfig,
    index: usize,
    revision: usize,
) -> Result<(), BenchError> {
    let path = root.join(relative_path(config, index));
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, body(config, index, revision))?;
    Ok(())
}

pub fn remove_file(root: &Path, config: &BenchConfig, index: usize) -> Result<(), BenchError> {
    fs::remove_file(root.join(relative_path(config, index)))?;
    Ok(())
}

pub fn ensure_empty_root(root: &Path) -> Result<(), BenchError> {
    match fs::read_dir(root) {
        Ok(mut entries) => {
            if entries.next().is_some() {
                return Err(BenchError::RootNotEmpty);
            }
            Ok(())
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            fs::create_dir_all(root)?;
            Ok(())
        }
        Err(error) => Err(error.into()),
    }
}

pub fn generate(root: &Path, config: &BenchConfig) -> Result<(), BenchError> {
    ensure_empty_root(root)?;
    for index in 0..config.files {
        write_file(root, config, index, 0)?;
    }
    Ok(())
}
