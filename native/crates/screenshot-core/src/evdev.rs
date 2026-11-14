use std::fs::{self, File, OpenOptions};
use std::io::Read;
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};

use rustix::event::{PollFd, PollFlags, Timespec, poll};

pub const EV_KEY: u16 = 1;
pub const KEY_SYSRQ: u16 = 99;
pub const KEY_PRINT: u16 = 210;
const EVENT_SIZE: usize = std::mem::size_of::<usize>()
    .saturating_mul(2)
    .saturating_add(8);
const MAX_DEVICES: usize = 32;
const O_NONBLOCK: i32 = 0o4000;

#[must_use]
pub fn is_print_press(chunk: &[u8]) -> bool {
    let offset = std::mem::size_of::<usize>().saturating_mul(2);
    let field = |from: usize, len: usize| chunk.get(from..from.saturating_add(len));
    let (Some(kind), Some(code), Some(value)) = (
        field(offset, 2).and_then(|b| <[u8; 2]>::try_from(b).ok()),
        field(offset.saturating_add(2), 2).and_then(|b| <[u8; 2]>::try_from(b).ok()),
        field(offset.saturating_add(4), 4).and_then(|b| <[u8; 4]>::try_from(b).ok()),
    ) else {
        return false;
    };
    u16::from_ne_bytes(kind) == EV_KEY
        && matches!(u16::from_ne_bytes(code), KEY_SYSRQ | KEY_PRINT)
        && i32::from_ne_bytes(value) == 1
}

#[must_use]
pub fn bit_set(bitmap: &str, bit: u16) -> bool {
    let word_bits = usize::BITS as usize;
    let words: Vec<&str> = bitmap.split_whitespace().collect();
    let index = usize::from(bit).checked_div(word_bits).unwrap_or(0);
    let within = usize::from(bit).checked_rem(word_bits).unwrap_or(0);
    words
        .iter()
        .rev()
        .nth(index)
        .and_then(|w| u64::from_str_radix(w, 16).ok())
        .is_some_and(|w| {
            w.checked_shr(u32::try_from(within).unwrap_or(0))
                .unwrap_or(0)
                & 1
                == 1
        })
}

#[must_use]
pub fn print_capable(capabilities: &str) -> bool {
    bit_set(capabilities, KEY_SYSRQ) || bit_set(capabilities, KEY_PRINT)
}

#[must_use]
pub fn discover(sys_input: &Path, dev_input: &Path) -> Vec<PathBuf> {
    let Ok(entries) = fs::read_dir(sys_input) else {
        return Vec::new();
    };
    let mut found: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|n| {
            n.strip_prefix("event")
                .is_some_and(|r| !r.is_empty() && r.bytes().all(|b| b.is_ascii_digit()))
        })
        .filter(|n| {
            fs::read_to_string(sys_input.join(n).join("device/capabilities/key"))
                .is_ok_and(|c| print_capable(&c))
        })
        .map(|n| dev_input.join(n))
        .collect();
    found.sort();
    found.truncate(MAX_DEVICES);
    found
}

#[derive(Debug, Default)]
pub struct Listener {
    files: Vec<(PathBuf, File)>,
}

impl Listener {
    pub fn rescan(&mut self, paths: &[PathBuf]) {
        self.files.retain(|(p, _)| paths.contains(p));
        for path in paths {
            if self.files.iter().any(|(p, _)| p == path) {
                continue;
            }
            if let Ok(file) = OpenOptions::new()
                .read(true)
                .custom_flags(O_NONBLOCK)
                .open(path)
            {
                self.files.push((path.clone(), file));
            }
        }
    }

    #[must_use]
    pub fn device_count(&self) -> usize {
        self.files.len()
    }

    pub fn wait_press(&mut self, timeout_ms: i64) -> bool {
        if self.files.is_empty() {
            std::thread::sleep(std::time::Duration::from_millis(
                u64::try_from(timeout_ms).unwrap_or(500),
            ));
            return false;
        }
        let mut fds: Vec<PollFd<'_>> = self
            .files
            .iter()
            .map(|(_, f)| PollFd::new(f, PollFlags::IN))
            .collect();
        let spec = Timespec {
            tv_sec: timeout_ms / 1000,
            tv_nsec: (timeout_ms % 1000).saturating_mul(1_000_000),
        };
        let ready = poll(&mut fds, Some(&spec)).unwrap_or(0);
        if ready == 0 {
            return false;
        }
        let flags: Vec<PollFlags> = fds.iter().map(PollFd::revents).collect();
        drop(fds);
        let mut pressed = false;
        let mut dead = Vec::new();
        for ((path, file), revents) in self.files.iter_mut().zip(flags) {
            if revents.intersects(PollFlags::ERR | PollFlags::HUP | PollFlags::NVAL) {
                dead.push(path.clone());
                continue;
            }
            if revents.contains(PollFlags::IN) {
                pressed |= drain(file);
            }
        }
        self.files.retain(|(p, _)| !dead.contains(p));
        pressed
    }
}

fn drain(file: &mut File) -> bool {
    let mut pressed = false;
    let mut buf = [0u8; EVENT_SIZE * 64];
    loop {
        match file.read(&mut buf) {
            Ok(0) | Err(_) => return pressed,
            Ok(n) => {
                pressed |= buf
                    .get(..n)
                    .unwrap_or_default()
                    .chunks_exact(EVENT_SIZE)
                    .any(is_print_press);
                buf.fill(0);
                if n < buf.len() {
                    return pressed;
                }
            }
        }
    }
}
