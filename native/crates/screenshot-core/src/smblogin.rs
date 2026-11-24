use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};

use crate::error::{Error, Result};

pub const FILE_NAME: &str = "smb.cred";
const MAX_USER: usize = 64;
const MAX_PASSWORD: usize = 256;

#[must_use]
pub fn valid_user(user: &str) -> bool {
    !user.is_empty()
        && user.len() <= MAX_USER
        && user
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-' | b'\\'))
        && user
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphanumeric)
}

#[must_use]
pub fn valid_password(password: &str) -> bool {
    !password.is_empty()
        && password.len() <= MAX_PASSWORD
        && !password.chars().any(char::is_control)
}

#[must_use]
pub fn render<S: std::hash::BuildHasher>(settings: &HashMap<String, String, S>) -> Option<String> {
    let user = settings
        .get("NUXIVA_SCREENSHOT_SMB_USER")
        .map(|v| v.trim())?;
    let password = settings.get("NUXIVA_SCREENSHOT_SMB_PASSWORD")?;
    if !valid_user(user) || !valid_password(password) {
        return None;
    }
    Some(format!("username = {user}\npassword = {password}\n"))
}

pub fn store(dir: &Path, content: &str) -> Result<PathBuf> {
    let path = dir.join(FILE_NAME);
    if fs::read(&path).is_ok_and(|current| current == content.as_bytes()) {
        return Ok(path);
    }
    let temp = dir.join(format!(".{FILE_NAME}.tmp"));
    let _ = fs::remove_file(&temp);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&temp)?;
    let written = file
        .write_all(content.as_bytes())
        .and_then(|()| file.sync_all());
    drop(file);
    if let Err(err) = written {
        let _ = fs::remove_file(&temp);
        return Err(Error::Io(err));
    }
    fs::rename(&temp, &path)?;
    Ok(path)
}
