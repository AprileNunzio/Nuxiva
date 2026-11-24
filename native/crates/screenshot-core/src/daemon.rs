use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use crate::bridge::{Bridge, RUNTIME_DIR, Status};
use crate::capture;
use crate::config::{Config, MAX_CONFIG_BYTES, Target, parse_env_text};
use crate::evdev::{Listener, discover};
use crate::naming::file_name;
use crate::notice::{Notice, show};
use crate::policy::{Deny, State, decide, guests_present};
use crate::raster::Raster;
use crate::retention::prune;
use crate::session::{Session, discover as discover_session};
use crate::sink::{Sink, build};
use crate::smblogin;
use crate::spool::{Backoff, Spool, flush};

const RESCAN_EVERY: Duration = Duration::from_secs(15);
const FLUSH_EVERY: Duration = Duration::from_secs(5);
const PRUNE_EVERY: Duration = Duration::from_hours(1);
const DEBOUNCE: Duration = Duration::from_millis(1500);
const POLL_MS: i64 = 500;
const STATE_DIR: &str = "/var/lib/nuxiva-screenshot";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Delivered,
    Queued,
    Denied(Deny),
    Failed,
}

pub fn log(message: &str) {
    eprintln!("nuxiva-screenshot: {message}");
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

fn hostname() -> String {
    fs::read_to_string("/proc/sys/kernel/hostname")
        .map(|h| h.trim().to_owned())
        .unwrap_or_default()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Format {
    Json,
    Env,
}

fn read_bounded(path: &Path) -> Option<String> {
    let text = fs::File::open(path).and_then(|f| {
        use std::io::Read;
        let mut buf = String::new();
        f.take(
            u64::try_from(MAX_CONFIG_BYTES)
                .unwrap_or(0)
                .saturating_add(1),
        )
        .read_to_string(&mut buf)
        .map(|_| buf)
    });
    text.ok()
}

#[must_use]
pub fn load_config(path: &Path, format: Format, default_target: Option<&Path>) -> Config {
    let Some(text) = read_bounded(path) else {
        return Config::default();
    };
    let mut config = match format {
        Format::Json => Config::parse(&text).unwrap_or_default(),
        Format::Env => {
            let mut settings = parse_env_text(&text);
            if let Some(dir) = default_target {
                settings
                    .entry("NUXIVA_SCREENSHOT_TARGET".to_owned())
                    .and_modify(|v| {
                        if v.trim().is_empty() {
                            *v = dir.to_string_lossy().into_owned();
                        }
                    })
                    .or_insert_with(|| dir.to_string_lossy().into_owned());
            }
            let mut config = Config::from_settings(&settings);
            attach_login(&mut config, &settings);
            config
        }
    };
    if config.target == Target::None {
        config.enabled = false;
    }
    config
}

fn state_dir() -> PathBuf {
    std::env::var("STATE_DIRECTORY")
        .ok()
        .and_then(|dirs| dirs.split(':').next().map(PathBuf::from))
        .filter(|p| p.is_absolute())
        .unwrap_or_else(|| PathBuf::from(STATE_DIR))
}

fn attach_login<S: std::hash::BuildHasher>(
    config: &mut Config,
    settings: &std::collections::HashMap<String, String, S>,
) {
    if !matches!(config.target, Target::Smb { .. }) {
        return;
    }
    let Some(content) = smblogin::render(settings) else {
        return;
    };
    match smblogin::store(&state_dir(), &content) {
        Ok(path) => config.smb_auth = path,
        Err(err) => log(&format!("smb_login_not_stored {}", err.code())),
    }
}

#[must_use]
pub fn folder(config: &Config) -> String {
    let sub = config.subdir.trim_matches('/');
    match &config.target {
        Target::None => String::new(),
        Target::Dir { path } => {
            let base = path.to_string_lossy();
            if sub.is_empty() {
                base.into_owned()
            } else {
                format!("{base}/{sub}")
            }
        }
        Target::Smb { host, share } => {
            let mut out = format!("\\\\{host}\\{share}");
            for part in sub.split('/').filter(|p| !p.is_empty()) {
                out.push('\\');
                out.push_str(part);
            }
            out
        }
    }
}

fn mtime(path: &Path) -> Option<SystemTime> {
    fs::metadata(path).and_then(|m| m.modified()).ok()
}

#[derive(Debug)]
pub struct Daemon {
    config_path: PathBuf,
    format: Format,
    default_target: Option<PathBuf>,
    config: Config,
    stamp: Option<SystemTime>,
    listener: Listener,
    backoff: Backoff,
    seq: u32,
    last_capture: Option<Instant>,
    spool: Option<Spool>,
    bridge: Bridge,
    last_name: String,
}

impl Daemon {
    #[must_use]
    pub fn new(config_path: PathBuf, format: Format, default_target: Option<PathBuf>) -> Self {
        Self {
            config_path,
            format,
            default_target,
            config: Config::default(),
            stamp: None,
            listener: Listener::default(),
            backoff: Backoff::new(),
            seq: 0,
            last_capture: None,
            spool: None,
            bridge: Bridge::new(PathBuf::from(RUNTIME_DIR)),
            last_name: String::new(),
        }
    }

    #[must_use]
    pub fn with_bridge(mut self, dir: PathBuf) -> Self {
        self.bridge = Bridge::new(dir);
        self
    }

    fn report(&mut self, status: Status, count: usize) {
        let name = if status == Status::Saved {
            self.last_name.clone()
        } else {
            String::new()
        };
        let folder = folder(&self.config);
        if let Err(err) = self.bridge.publish(status, &name, &folder, count) {
            log(&format!("status_not_published {}", err.code()));
        }
    }

    #[must_use]
    pub fn status_of(outcome: Outcome) -> Status {
        match outcome {
            Outcome::Delivered => Status::Saved,
            Outcome::Queued => Status::Queued,
            Outcome::Denied(Deny::Disabled) => Status::Disabled,
            Outcome::Denied(Deny::NoTarget) => Status::NoTarget,
            Outcome::Denied(_) => Status::Blocked,
            Outcome::Failed => Status::Failed,
        }
    }

    pub fn capture_now(&mut self, session: Option<&Session>, now: Instant) -> Outcome {
        let outcome = self.handle_trigger(session, now);
        let status = match (Self::status_of(outcome), &self.config.target) {
            (Status::Disabled, Target::None) => Status::NoTarget,
            (status, _) => status,
        };
        self.report(status, 0);
        outcome
    }

    pub fn reload(&mut self) {
        let stamp = mtime(&self.config_path);
        if stamp == self.stamp && self.spool.is_some() {
            return;
        }
        self.stamp = stamp;
        self.config = load_config(
            &self.config_path,
            self.format,
            self.default_target.as_deref(),
        );
        self.spool = Spool::open(self.config.spool.clone()).ok();
        log(&format!(
            "config enabled={} target={}",
            self.config.enabled,
            self.config.active()
        ));
    }

    pub fn handle_trigger(&mut self, session: Option<&Session>, now: Instant) -> Outcome {
        let state = State {
            locked: session.is_some_and(|s| s.locked),
            guests: guests_present(&self.config.guest_flag),
        };
        if let Err(reason) = decide(&self.config, state) {
            if self.config.enabled && self.config.notice {
                if let Some(s) = session {
                    show(s, &self.config.lang, Notice::Blocked);
                }
            }
            return Outcome::Denied(reason);
        }
        let Some(spool) = self.spool.as_ref() else {
            return Outcome::Failed;
        };
        let Ok(mut bytes) = capture::grab(session) else {
            self.notify(session, Notice::Failed);
            return Outcome::Failed;
        };
        if !self.config.masks.is_empty() {
            let masked = Raster::decode(&bytes).and_then(|mut r| {
                r.apply_masks(&self.config.masks);
                r.encode()
            });
            if let Ok(masked) = masked {
                bytes = masked;
            } else {
                self.notify(session, Notice::Failed);
                return Outcome::Failed;
            }
        }
        let name = file_name(&hostname(), now_secs(), self.seq);
        self.seq = self.seq.wrapping_add(1);
        name.clone_into(&mut self.last_name);
        if spool.enqueue(&name, &bytes).is_err() {
            self.notify(session, Notice::Failed);
            return Outcome::Failed;
        }
        let Some(sink) = build(&self.config) else {
            return Outcome::Queued;
        };
        let report = flush(spool, sink.as_ref(), &mut self.backoff, now);
        let outcome = if report.failed || spool_has_pending(self.spool.as_ref()) {
            Outcome::Queued
        } else {
            Outcome::Delivered
        };
        self.notify(
            session,
            if outcome == Outcome::Delivered {
                Notice::Saved
            } else {
                Notice::Queued
            },
        );
        outcome
    }

    fn notify(&self, session: Option<&Session>, notice: Notice) {
        if self.config.notice {
            if let Some(s) = session {
                show(s, &self.config.lang, notice);
            }
        }
    }

    fn retry(&mut self, now: Instant) {
        let (Some(spool), Some(sink)) = (self.spool.as_ref(), build(&self.config)) else {
            return;
        };
        if self.config.active() && !spool.pending().is_empty() {
            let report = flush(spool, sink.as_ref(), &mut self.backoff, now);
            if report.delivered > 0 {
                log(&format!("flushed {}", report.delivered));
                self.report(Status::DeliveredLater, report.delivered);
            }
        }
    }

    fn retention(&self) {
        if !self.config.active() {
            return;
        }
        if let Some(sink) = build(&self.config) {
            let removed = prune(sink.as_ref(), &self.config.retention, now_secs());
            if removed > 0 {
                log(&format!("pruned {removed}"));
            }
        }
    }

    pub fn run(&mut self) -> ! {
        let mut last_scan: Option<Instant> = None;
        let mut last_flush = Instant::now();
        let mut last_prune: Option<Instant> = None;
        loop {
            let now = Instant::now();
            self.reload();
            if self.config.enabled
                && last_scan.is_none_or(|t| now.duration_since(t) >= RESCAN_EVERY)
            {
                let paths = discover(Path::new("/sys/class/input"), Path::new("/dev/input"));
                self.listener.rescan(&paths);
                last_scan = Some(now);
            }
            if !self.config.enabled {
                if self.bridge.take_request() {
                    let outcome = self.capture_now(None, now);
                    log(&format!("request {outcome:?}"));
                }
                std::thread::sleep(Duration::from_millis(500));
                continue;
            }
            let pressed = self.listener.wait_press(POLL_MS);
            let requested = self.bridge.take_request();
            if (pressed || requested)
                && self
                    .last_capture
                    .is_none_or(|t| now.duration_since(t) >= DEBOUNCE)
            {
                self.last_capture = Some(now);
                let session = discover_session();
                let outcome = self.capture_now(session.as_ref(), now);
                log(&format!("trigger {outcome:?}"));
            }
            if now.duration_since(last_flush) >= FLUSH_EVERY {
                last_flush = now;
                self.retry(now);
            }
            if last_prune.is_none_or(|t| now.duration_since(t) >= PRUNE_EVERY) {
                last_prune = Some(now);
                self.retention();
            }
        }
    }
}

fn spool_has_pending(spool: Option<&Spool>) -> bool {
    spool.is_some_and(|s| !s.pending().is_empty())
}

#[must_use]
pub fn sink_for(config: &Config) -> Option<Box<dyn Sink>> {
    build(config)
}
