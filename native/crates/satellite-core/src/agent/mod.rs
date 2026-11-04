pub mod report;
pub mod service;

use std::time::{Duration, Instant};

use serde_json::Value;

use crate::backends::Descriptor;
use crate::link::{Link, LinkError};
use crate::plan::{Plan, plan};
use crate::probe::root::Root;
use crate::probe::{Profile, profile, system};

const MIN_INTERVAL: u64 = 10;
const MAX_INTERVAL: u64 = 300;
const REPROBE_EVERY: Duration = Duration::from_secs(120);
const COMMANDS_MAX: usize = 5;

#[derive(Debug, PartialEq, Eq)]
pub enum Exit {
    Revoked,
    Restart,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    Adapt,
    Restart,
    Identify,
    Unsupported(String),
}

pub fn parse_commands(reply: &Value) -> Vec<Command> {
    reply
        .get("commands")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .take(COMMANDS_MAX)
                .filter_map(Value::as_str)
                .map(|name| match name {
                    "adapt" => Command::Adapt,
                    "restart" => Command::Restart,
                    "identify" => Command::Identify,
                    other => Command::Unsupported(other.chars().take(24).collect()),
                })
                .collect()
        })
        .unwrap_or_default()
}

pub fn next_interval(reply: &Value) -> u64 {
    reply
        .get("heartbeat")
        .and_then(Value::as_u64)
        .unwrap_or(30)
        .clamp(MIN_INTERVAL, MAX_INTERVAL)
}

#[derive(Debug)]
pub struct Runner {
    root: Root,
    descriptors: Vec<Descriptor>,
    library_dirs: Vec<String>,
    profile: Profile,
    plan: Plan,
    probed: Instant,
    adapted: bool,
}

impl Runner {
    #[must_use]
    pub fn new(root: Root, descriptors: Vec<Descriptor>, library_dirs: Vec<String>) -> Self {
        let profile = profile(&root, &descriptors, &library_dirs);
        let plan = plan(&profile);
        Self {
            root,
            descriptors,
            library_dirs,
            profile,
            plan,
            probed: Instant::now(),
            adapted: false,
        }
    }

    pub fn reprobe(&mut self) -> bool {
        let fresh = profile(&self.root, &self.descriptors, &self.library_dirs);
        let changed =
            fresh.accelerators != self.profile.accelerators || fresh.senses != self.profile.senses;
        self.plan = plan(&fresh);
        self.profile = fresh;
        self.probed = Instant::now();
        changed
    }

    #[must_use]
    pub fn profile(&self) -> &Profile {
        &self.profile
    }

    #[must_use]
    pub fn plan(&self) -> &Plan {
        &self.plan
    }

    pub fn report(&mut self) -> Value {
        if self.probed.elapsed() >= REPROBE_EVERY && self.reprobe() {
            log("hardware_changed");
        }
        let metrics = system::metrics(&self.root, self.profile.system.cores);
        let adapted = std::mem::take(&mut self.adapted);
        report::heartbeat(&self.profile, &self.plan, &metrics, adapted)
    }

    pub fn run(&mut self, link: &Link) -> Result<Exit, LinkError> {
        let mut backoff = 5u64;
        loop {
            let wait = match link.post("/api/nodes/heartbeat", &self.report()) {
                Ok(reply) => {
                    backoff = 5;
                    if let Some(exit) = self.apply(&reply) {
                        return Ok(exit);
                    }
                    if self.adapted {
                        1
                    } else {
                        next_interval(&reply)
                    }
                }
                Err(LinkError::Unauthorized) => return Ok(Exit::Revoked),
                Err(error @ LinkError::Pin(_)) => return Err(error),
                Err(error) => {
                    log(&format!("heartbeat_failed {error}"));
                    backoff = backoff.saturating_mul(2).min(MAX_INTERVAL);
                    backoff
                }
            };
            std::thread::sleep(Duration::from_secs(wait));
        }
    }

    fn apply(&mut self, reply: &Value) -> Option<Exit> {
        for command in parse_commands(reply) {
            match command {
                Command::Adapt => {
                    self.reprobe();
                    self.adapted = true;
                    log("adapted");
                }
                Command::Restart => return Some(Exit::Restart),
                Command::Identify => log(&format!("identify {}", self.profile.system.hostname)),
                Command::Unsupported(name) => log(&format!("command_unsupported {name}")),
            }
        }
        None
    }
}

pub fn log(message: &str) {
    eprintln!("nuxiva-satellite: {message}");
}
