use std::collections::{BTreeSet, HashMap, HashSet};

use crate::levels::Risk;

pub const MAX_TARGETS: usize = 1024;
pub const MAX_TEXT: usize = 256;
pub const CRITICAL_CAP: &str = "risk.critical";

#[derive(Debug, Clone)]
pub struct HomeTables {
    pub domains: HashMap<String, Risk>,
    pub unknown: Risk,
    pub read_private: HashSet<String>,
    pub sensitive_covers: HashSet<String>,
    pub appliances: HashSet<String>,
    pub climate: HashSet<String>,
    pub gate_open: HashSet<String>,
    pub comfort: (f64, f64),
}

#[derive(Debug, Clone, Copy)]
pub struct Target<'a> {
    pub domain: &'a str,
    pub device_class: &'a str,
}

#[derive(Debug, Clone)]
pub struct HomeRules {
    tables: HomeTables,
}

fn too_long(text: &str) -> bool {
    text.len() > MAX_TEXT
}

impl HomeRules {
    #[must_use]
    pub fn new(tables: HomeTables) -> Self {
        Self { tables }
    }

    fn bounded(declared: &str, service: &str, targets: &[Target<'_>]) -> bool {
        targets.len() <= MAX_TARGETS
            && !too_long(declared)
            && !too_long(service)
            && targets
                .iter()
                .all(|t| !too_long(t.domain) && !too_long(t.device_class))
    }

    fn sensitive_cover(&self, device_class: &str) -> bool {
        self.tables.sensitive_covers.contains(device_class)
    }

    fn domain_risk(&self, domain: &str) -> Risk {
        self.tables
            .domains
            .get(domain)
            .copied()
            .unwrap_or(self.tables.unknown)
    }

    #[must_use]
    pub fn sensitive(&self, domain: &str, service: &str, device_class: &str) -> bool {
        match domain {
            "lock" => matches!(service, "unlock" | "open"),
            "alarm_control_panel" => service == "alarm_disarm",
            "cover" => {
                self.sensitive_cover(device_class)
                    && matches!(service, "open_cover" | "set_cover_position")
            }
            "valve" => service == "open_valve",
            _ => false,
        }
    }

    #[must_use]
    pub fn service_risk(&self, domain: &str, service: &str, device_class: &str) -> Risk {
        if self.sensitive(domain, service, device_class) {
            return Risk::Critical;
        }
        let level = self.domain_risk(domain);
        if domain == "cover" && self.sensitive_cover(device_class) {
            return level.max(Risk::Personal);
        }
        level
    }

    fn declared_extra(declared: &str, targets: &[Target<'_>]) -> bool {
        !declared.is_empty() && targets.iter().all(|t| t.domain != declared)
    }

    #[must_use]
    pub fn call_risk(&self, declared: &str, service: &str, targets: &[Target<'_>]) -> Risk {
        if !Self::bounded(declared, service, targets) {
            return Risk::Critical;
        }
        let fallback = [Target {
            domain: declared,
            device_class: "",
        }];
        let chosen = if targets.is_empty() {
            &fallback[..]
        } else {
            targets
        };
        let worst = chosen
            .iter()
            .map(|t| self.service_risk(t.domain, service, t.device_class))
            .max()
            .unwrap_or(Risk::Critical);
        if Self::declared_extra(declared, chosen) {
            return worst.max(self.domain_risk(declared));
        }
        worst
    }

    #[must_use]
    pub fn read_private(&self, domains: &[&str]) -> bool {
        domains
            .iter()
            .any(|d| self.tables.read_private.contains(*d))
    }

    #[must_use]
    pub fn read_risk(&self, domains: &[&str]) -> Risk {
        if domains.len() > MAX_TARGETS || domains.iter().any(|d| too_long(d)) {
            return Risk::Critical;
        }
        if self.read_private(domains) {
            Risk::Personal
        } else {
            Risk::Home
        }
    }

    #[must_use]
    pub fn read_capability(&self, domains: &[&str]) -> &'static str {
        if domains.len() > MAX_TARGETS || domains.iter().any(|d| too_long(d)) {
            return CRITICAL_CAP;
        }
        if self.read_private(domains) {
            "home.private.read"
        } else {
            "home.state.read"
        }
    }

    fn comfy(&self, service: &str, temperature: Option<f64>) -> bool {
        let (low, high) = self.tables.comfort;
        service == "set_temperature" && temperature.is_some_and(|v| low <= v && v <= high)
    }

    #[must_use]
    pub fn capability(
        &self,
        domain: &str,
        service: &str,
        device_class: &str,
        temperature: Option<f64>,
    ) -> &'static str {
        match domain {
            "light" => "home.light.set",
            "fan" => "home.comfort.set",
            "media_player" | "remote" => "media.tv.watch",
            "scene" => "home.scene.activate",
            "cover" if self.sensitive_cover(device_class) => {
                if self.tables.gate_open.contains(service) {
                    "home.gate.open"
                } else {
                    "home.gate.close"
                }
            }
            "cover" => "home.cover.set",
            "lock" if service == "lock" => "home.lock.lock",
            "lock" => "home.lock.unlock",
            "alarm_control_panel" if service.starts_with("alarm_arm") => "home.alarm.arm",
            "alarm_control_panel" => "home.alarm.disarm",
            d if self.tables.climate.contains(d) => {
                if self.comfy(service, temperature) {
                    "home.climate.adjust"
                } else {
                    "home.climate.set"
                }
            }
            "valve" => "home.valve.set",
            d if self.tables.appliances.contains(d) => "home.appliance.set",
            "camera" => "home.camera.manage",
            "automation" | "script" => "home.automation.run",
            "homeassistant" => "home.system.manage",
            _ => CRITICAL_CAP,
        }
    }

    #[must_use]
    pub fn call_capabilities(
        &self,
        declared: &str,
        service: &str,
        targets: &[Target<'_>],
        temperature: Option<f64>,
    ) -> Vec<&'static str> {
        if !Self::bounded(declared, service, targets) {
            return vec![CRITICAL_CAP];
        }
        let fallback = [Target {
            domain: declared,
            device_class: "",
        }];
        let chosen = if targets.is_empty() {
            &fallback[..]
        } else {
            targets
        };
        let mut caps: BTreeSet<&'static str> = chosen
            .iter()
            .map(|t| self.capability(t.domain, service, t.device_class, temperature))
            .collect();
        if Self::declared_extra(declared, chosen) {
            caps.insert(self.capability(declared, service, "", temperature));
        }
        caps.into_iter().collect()
    }
}
