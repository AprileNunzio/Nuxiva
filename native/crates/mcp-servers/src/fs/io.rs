use std::fs::{self, File, OpenOptions};
use std::io::{self, Read};
use std::path::Path;

use time::OffsetDateTime;
use time::macros::format_description;

use super::paths::Fault;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    File(u64),
    Dir,
}

pub fn kind_of(path: &Path) -> Result<Kind, Fault> {
    match fs::symlink_metadata(path) {
        Ok(meta) if meta.is_file() => Ok(Kind::File(meta.len())),
        Ok(meta) if meta.is_dir() => Ok(Kind::Dir),
        Ok(_) => Err(Fault::Special),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Err(Fault::Missing),
        Err(_) => Err(Fault::Io),
    }
}

pub fn exists(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok()
}

#[cfg(unix)]
fn no_follow(options: &mut OpenOptions) -> &mut OpenOptions {
    use std::os::unix::fs::OpenOptionsExt;
    options.custom_flags(libc::O_NOFOLLOW)
}

#[cfg(not(unix))]
fn no_follow(options: &mut OpenOptions) -> &mut OpenOptions {
    options
}

pub fn open_read(path: &Path) -> io::Result<File> {
    let mut options = OpenOptions::new();
    no_follow(options.read(true)).open(path)
}

pub fn open_write(path: &Path, append: bool) -> io::Result<File> {
    let mut options = OpenOptions::new();
    options.write(true).create(true);
    if append {
        options.append(true);
    } else {
        options.truncate(true);
    }
    no_follow(&mut options).open(path)
}

pub fn read_limited(path: &Path, limit: u64) -> Result<Vec<u8>, Fault> {
    let mut file = open_read(path).map_err(|_| Fault::Io)?;
    let mut data = Vec::new();
    file.by_ref()
        .take(limit.saturating_add(1))
        .read_to_end(&mut data)
        .map_err(|_| Fault::Io)?;
    if u64::try_from(data.len()).unwrap_or(u64::MAX) > limit {
        return Err(Fault::TooBig);
    }
    Ok(data)
}

pub fn size_text(bytes: u64) -> String {
    let units = ["B", "KB", "MB", "GB", "TB"];
    let mut value = bytes;
    let mut index = 0usize;
    while value >= 1024 && index < units.len().saturating_sub(1) {
        value = value.checked_div(1024).unwrap_or(0);
        index = index.saturating_add(1);
    }
    format!("{value} {}", units.get(index).copied().unwrap_or("B"))
}

pub fn date_text(path: &Path) -> String {
    let modified = fs::metadata(path)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .and_then(|d| i64::try_from(d.as_secs()).ok())
        .and_then(|s| OffsetDateTime::from_unix_timestamp(s).ok());
    modified
        .and_then(|m| {
            m.format(format_description!(
                "[day]/[month]/[year] [hour]:[minute] UTC"
            ))
            .ok()
        })
        .unwrap_or_else(|| "data sconosciuta".to_owned())
}

pub fn stamp() -> String {
    OffsetDateTime::now_utc()
        .format(format_description!(
            "[year][month][day]-[hour][minute][second]"
        ))
        .unwrap_or_else(|_| "00000000-000000".to_owned())
}
