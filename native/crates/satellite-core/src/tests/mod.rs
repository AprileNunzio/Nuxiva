mod agent;
mod boards;
mod extend;
mod link;
mod plan;
mod vault;

use std::fmt::Write;
use std::fs;
use std::path::PathBuf;

use crate::probe::root::Root;

pub struct Fixture {
    dir: PathBuf,
}

impl Fixture {
    pub fn new(tag: &str) -> Result<Self, String> {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).map_err(|e| e.to_string())?;
        let suffix = u64::from_le_bytes(nonce);
        let dir = std::env::temp_dir().join(format!("nxs-{tag}-{suffix:016x}"));
        fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
        Ok(Self { dir })
    }

    pub fn file(&self, path: &str, content: &str) -> Result<&Self, String> {
        let full = self.dir.join(path.trim_start_matches('/'));
        if let Some(parent) = full.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        fs::write(&full, content).map_err(|e| e.to_string())?;
        Ok(self)
    }

    pub fn dir(&self, path: &str) -> Result<&Self, String> {
        fs::create_dir_all(self.dir.join(path.trim_start_matches('/')))
            .map_err(|e| e.to_string())?;
        Ok(self)
    }

    pub fn link(&self, path: &str, target: &str) -> Result<&Self, String> {
        let full = self.dir.join(path.trim_start_matches('/'));
        if let Some(parent) = full.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        std::os::unix::fs::symlink(target, full).map_err(|e| e.to_string())?;
        Ok(self)
    }

    pub fn root(&self) -> Root {
        Root::new(&self.dir)
    }

    pub fn path(&self) -> PathBuf {
        self.dir.clone()
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.dir);
    }
}

pub fn base(fx: &Fixture, cores: usize, ram_kb: u64) -> Result<(), String> {
    let cpuinfo = (0..cores).fold(String::new(), |mut out, i| {
        let _ = write!(
            out,
            "processor\t: {i}\nFeatures\t: fp asimd asimddp i8mm\n\n"
        );
        out
    });
    fx.file("/proc/cpuinfo", &cpuinfo)?
        .file(
            "/proc/meminfo",
            &format!(
                "MemTotal:       {ram_kb} kB\nMemAvailable:   {} kB\n",
                ram_kb >> 1
            ),
        )?
        .file("/proc/loadavg", "0.50 0.40 0.30 1/100 1234\n")?
        .file("/proc/uptime", "3600.5 100.0\n")?
        .file("/proc/sys/kernel/hostname", "salotto\n")?
        .file(
            "/etc/os-release",
            "NAME=Debian\nPRETTY_NAME=\"Debian GNU/Linux 13 (trixie)\"\n",
        )?
        .file("/sys/class/thermal/thermal_zone0/temp", "47260\n")?;
    Ok(())
}

pub fn microphone_and_speaker(fx: &Fixture) -> Result<(), String> {
    fx.file(
        "/proc/asound/cards",
        " 0 [Device         ]: USB-Audio - USB PnP Sound Device\n                      C-Media USB PnP\n",
    )?
    .dir("/proc/asound/card0/pcm0c")?
    .dir("/proc/asound/card0/pcm0p")?;
    Ok(())
}

pub fn camera(fx: &Fixture, name: &str) -> Result<(), String> {
    fx.file("/sys/class/video4linux/video0/name", name)?
        .file("/sys/class/video4linux/video0/index", "0\n")?
        .file("/sys/class/video4linux/video1/name", name)?
        .file("/sys/class/video4linux/video1/index", "1\n")?;
    Ok(())
}
