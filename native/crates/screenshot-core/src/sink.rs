use std::fmt::Write as _;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

use crate::config::{Config, SMB_AUTH_FILE, Target};
use crate::error::{Error, Result};
use crate::naming::{is_managed, stamp_secs};
use crate::pathguard::{ALLOWED_ROOTS, resolve_dir_in};
use crate::proc::run_bounded;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub name: String,
    pub size: u64,
    pub stamp: u64,
}

pub trait Sink {
    fn put(&self, name: &str, data: &[u8]) -> Result<()>;
    fn list(&self) -> Result<Vec<Entry>>;
    fn remove(&self, name: &str) -> Result<()>;
}

#[derive(Debug)]
pub struct DirSink {
    root: PathBuf,
    subdir: String,
    roots: Vec<String>,
}

impl DirSink {
    #[must_use]
    pub fn new(root: PathBuf, subdir: String) -> Self {
        let roots = ALLOWED_ROOTS.iter().map(|r| (*r).to_owned()).collect();
        Self::with_roots(root, subdir, roots)
    }

    #[must_use]
    pub fn with_roots(root: PathBuf, subdir: String, roots: Vec<String>) -> Self {
        Self {
            root,
            subdir,
            roots,
        }
    }

    fn dir(&self) -> Result<PathBuf> {
        let roots: Vec<&str> = self.roots.iter().map(String::as_str).collect();
        resolve_dir_in(&self.root, &self.subdir, &roots)
    }
}

fn temp_name() -> Result<String> {
    let mut raw = [0u8; 8];
    getrandom::fill(&mut raw).map_err(|_| Error::Sink("random".into()))?;
    let mut name = String::from(".tmp-");
    for byte in raw {
        let _ = write!(name, "{byte:02x}");
    }
    Ok(name)
}

pub fn atomic_write(dir: &Path, name: &str, data: &[u8], mode: u32) -> Result<()> {
    if !is_managed(name) {
        return Err(Error::Path("name"));
    }
    let final_path = dir.join(name);
    if fs::symlink_metadata(&final_path).is_ok() {
        return Err(Error::Sink("exists".into()));
    }
    let tmp = dir.join(temp_name()?);
    let result = (|| -> Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(mode)
            .open(&tmp)?;
        file.write_all(data)?;
        file.sync_all()?;
        fs::hard_link(&tmp, &final_path)?;
        Ok(())
    })();
    let _ = fs::remove_file(&tmp);
    result?;
    if let Ok(handle) = fs::File::open(dir) {
        let _ = handle.sync_all();
    }
    Ok(())
}

impl Sink for DirSink {
    fn put(&self, name: &str, data: &[u8]) -> Result<()> {
        atomic_write(&self.dir()?, name, data, 0o640)
    }

    fn list(&self) -> Result<Vec<Entry>> {
        let dir = self.dir()?;
        let mut out = Vec::new();
        for entry in fs::read_dir(dir)?.filter_map(std::result::Result::ok) {
            let Ok(name) = entry.file_name().into_string() else {
                continue;
            };
            let Some(stamp) = stamp_secs(&name) else {
                continue;
            };
            let Ok(meta) = fs::symlink_metadata(entry.path()) else {
                continue;
            };
            if meta.is_file() {
                out.push(Entry {
                    name,
                    size: meta.len(),
                    stamp,
                });
            }
        }
        Ok(out)
    }

    fn remove(&self, name: &str) -> Result<()> {
        if !is_managed(name) {
            return Err(Error::Path("name"));
        }
        fs::remove_file(self.dir()?.join(name)).map_err(Error::Io)
    }
}

#[derive(Debug)]
pub struct SmbSink {
    host: String,
    share: String,
    subdir: String,
    auth: PathBuf,
}

const SMB_TIMEOUT: Duration = Duration::from_mins(1);

impl SmbSink {
    #[must_use]
    pub fn new(host: String, share: String, subdir: String) -> Self {
        Self {
            host,
            share,
            subdir,
            auth: PathBuf::from(SMB_AUTH_FILE),
        }
    }

    fn run(&self, script: &str) -> Result<Vec<u8>> {
        let meta =
            fs::symlink_metadata(&self.auth).map_err(|_| Error::Sink("auth_missing".into()))?;
        if !meta.is_file() {
            return Err(Error::Sink("auth_invalid".into()));
        }
        let mut command = Command::new("smbclient");
        command
            .arg(format!("//{}/{}", self.host, self.share))
            .arg("-A")
            .arg(&self.auth)
            .args(["-m", "SMB3", "-c", script])
            .env_clear()
            .env("PATH", "/usr/local/bin:/usr/bin:/bin")
            .stdin(Stdio::null());
        run_bounded(&mut command, SMB_TIMEOUT, 4 * 1024 * 1024)
            .ok_or_else(|| Error::Sink("smbclient".into()))
    }

    fn cd(&self) -> String {
        if self.subdir.is_empty() {
            String::new()
        } else {
            format!("cd \"{}\"; ", self.subdir)
        }
    }

    fn mkdirs(&self) -> String {
        let mut acc = String::new();
        let mut path = String::new();
        for part in self.subdir.split('/').filter(|p| !p.is_empty()) {
            if !path.is_empty() {
                path.push('/');
            }
            path.push_str(part);
            let _ = write!(acc, "mkdir \"{path}\"; ");
        }
        acc
    }
}

#[must_use]
pub fn parse_smb_ls(text: &str) -> Vec<Entry> {
    text.lines()
        .filter_map(|line| {
            let mut tokens = line.split_whitespace();
            let name = tokens.next()?;
            let _attrs = tokens.next()?;
            let size: u64 = tokens.next()?.parse().ok()?;
            Some(Entry {
                name: name.to_owned(),
                size,
                stamp: stamp_secs(name)?,
            })
        })
        .collect()
}

impl Sink for SmbSink {
    fn put(&self, name: &str, data: &[u8]) -> Result<()> {
        if !is_managed(name) {
            return Err(Error::Path("name"));
        }
        let local = std::env::temp_dir().join(temp_name()?);
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&local)?;
        let written = file.write_all(data).and_then(|()| file.sync_all());
        drop(file);
        let script = format!("{}put \"{}\" \"{name}\"", self.cd(), local.display());
        let outcome = written.map_err(Error::Io).and_then(|()| {
            let dirs = self.mkdirs();
            if !dirs.is_empty() {
                let _ = self.run(&dirs);
            }
            self.run(&script)
        });
        let _ = fs::remove_file(&local);
        outcome.map(|_| ())
    }

    fn list(&self) -> Result<Vec<Entry>> {
        let out = self.run(&format!("{}ls *.png", self.cd()))?;
        Ok(parse_smb_ls(&String::from_utf8_lossy(&out)))
    }

    fn remove(&self, name: &str) -> Result<()> {
        if !is_managed(name) {
            return Err(Error::Path("name"));
        }
        self.run(&format!("{}del \"{name}\"", self.cd()))
            .map(|_| ())
    }
}

#[must_use]
pub fn build(config: &Config) -> Option<Box<dyn Sink>> {
    match &config.target {
        Target::None => None,
        Target::Dir { path } => Some(Box::new(DirSink::new(path.clone(), config.subdir.clone()))),
        Target::Smb { host, share } => Some(Box::new(SmbSink::new(
            host.clone(),
            share.clone(),
            config.subdir.clone(),
        ))),
    }
}
