use serde::Serialize;
use sha2::{Digest, Sha256};

const MAX_PACKAGES: usize = 4000;
const MAX_NAME: usize = 100;
const REBOOT_PREFIXES: [&str; 6] = ["linux-image-", "libc6", "systemd", "udev", "dbus", "grub-"];

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AptChange {
    pub name: String,
    pub from: String,
    pub to: String,
    pub security: bool,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct AptSimulation {
    pub upgrades: Vec<AptChange>,
    pub installs: Vec<String>,
    pub removals: Vec<String>,
    pub kept_back: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PlanStep {
    pub id: &'static str,
    pub count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Plan {
    pub id: String,
    pub steps: Vec<PlanStep>,
    pub packages: usize,
    pub security: usize,
    pub installs: usize,
    pub removals: usize,
    pub kept_back: usize,
    pub nuxiva: bool,
    pub reboot_likely: bool,
    pub risk: &'static str,
    pub needs_confirmation: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ConfigFile {
    pub name: &'static str,
    pub content: String,
}

#[must_use]
pub fn valid_package_name(name: &str) -> bool {
    let mut chars = name.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    name.len() <= MAX_NAME
        && first.is_ascii_alphanumeric()
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '+' | '-' | ':'))
}

fn token(raw: &str) -> String {
    raw.trim_matches(|c| matches!(c, '[' | ']' | '(' | ')' | ','))
        .chars()
        .filter(|c| !c.is_control())
        .take(MAX_NAME)
        .collect()
}

fn parse_inst(rest: &str) -> Option<(AptChange, bool)> {
    let mut parts = rest.split_whitespace();
    let name = parts.next()?;
    if !valid_package_name(name) {
        return None;
    }
    let second = parts.next()?;
    let (from, target) = if second.starts_with('[') {
        (token(second), parts.next()?)
    } else {
        (String::new(), second)
    };
    let to = token(target);
    let origin: String = parts
        .take_while(|p| !p.starts_with('['))
        .collect::<Vec<_>>()
        .join(" ");
    let security = origin.to_ascii_lowercase().contains("security");
    let is_new = from.is_empty();
    Some((
        AptChange {
            name: name.to_owned(),
            from,
            to,
            security,
        },
        is_new,
    ))
}

#[must_use]
pub fn parse_simulation(raw: &str) -> AptSimulation {
    let mut sim = AptSimulation::default();
    let mut in_kept = false;
    for line in raw.lines() {
        if line.starts_with("The following packages have been kept back") {
            in_kept = true;
            continue;
        }
        if in_kept {
            if line.starts_with(' ') {
                for name in line.split_whitespace() {
                    if valid_package_name(name) && sim.kept_back.len() < MAX_PACKAGES {
                        sim.kept_back.push(name.to_owned());
                    }
                }
                continue;
            }
            in_kept = false;
        }
        if let Some(rest) = line.strip_prefix("Inst ") {
            if sim.upgrades.len().saturating_add(sim.installs.len()) >= MAX_PACKAGES {
                continue;
            }
            if let Some((change, is_new)) = parse_inst(rest) {
                if is_new {
                    sim.installs.push(change.name);
                } else {
                    sim.upgrades.push(change);
                }
            }
        } else if let Some(rest) = line.strip_prefix("Remv ") {
            if let Some(name) = rest.split_whitespace().next() {
                if valid_package_name(name) && sim.removals.len() < MAX_PACKAGES {
                    sim.removals.push(name.to_owned());
                }
            }
        }
    }
    sim
}

fn reboot_package(name: &str) -> bool {
    REBOOT_PREFIXES
        .iter()
        .any(|p| name == p.trim_end_matches('-') || name.starts_with(p))
}

fn plan_id(sim: &AptSimulation, nuxiva_target: &str) -> String {
    let mut lines: Vec<String> = sim
        .upgrades
        .iter()
        .map(|c| format!("u|{}|{}", c.name, c.to))
        .chain(sim.installs.iter().map(|n| format!("i|{n}")))
        .chain(sim.removals.iter().map(|n| format!("r|{n}")))
        .collect();
    lines.sort_unstable();
    lines.push(format!("n|{nuxiva_target}"));
    let digest = Sha256::digest(lines.join("\n").as_bytes());
    let mut out = String::with_capacity(16);
    for b in digest.iter().take(8) {
        out.extend(char::from_digit(u32::from(b >> 4), 16));
        out.extend(char::from_digit(u32::from(b & 0x0f), 16));
    }
    out
}

#[must_use]
pub fn build_plan(sim: &AptSimulation, nuxiva_available: bool, nuxiva_target: &str) -> Plan {
    let packages = sim.upgrades.len().saturating_add(sim.installs.len());
    let security = sim.upgrades.iter().filter(|c| c.security).count();
    let reboot_likely = sim.upgrades.iter().any(|c| reboot_package(&c.name))
        || sim.installs.iter().any(|n| reboot_package(n));
    let removals = sim.removals.len();
    let installs = sim.installs.len();
    let risk = if removals > 0 {
        "high"
    } else if reboot_likely || installs > 0 {
        "medium"
    } else {
        "low"
    };
    let mut steps = Vec::new();
    if packages > 0 || removals > 0 {
        steps.push(PlanStep {
            id: "debian",
            count: packages.saturating_add(removals),
        });
    }
    if nuxiva_available {
        steps.push(PlanStep {
            id: "nuxiva",
            count: 1,
        });
    }
    Plan {
        id: plan_id(sim, if nuxiva_available { nuxiva_target } else { "" }),
        steps,
        packages,
        security,
        installs,
        removals,
        kept_back: sim.kept_back.len(),
        nuxiva: nuxiva_available,
        reboot_likely,
        risk,
        needs_confirmation: removals > 0,
    }
}

#[must_use]
pub fn render_auto_config(enabled: bool) -> Vec<ConfigFile> {
    let flag = if enabled { "1" } else { "0" };
    vec![
        ConfigFile {
            name: "20nuxiva-auto-upgrades",
            content: format!(
                "APT::Periodic::Update-Package-Lists \"{flag}\";\nAPT::Periodic::Unattended-Upgrade \"{flag}\";\n"
            ),
        },
        ConfigFile {
            name: "52nuxiva-unattended-upgrades",
            content: concat!(
                "#clear Unattended-Upgrade::Origins-Pattern;\n",
                "Unattended-Upgrade::Origins-Pattern {\n",
                "    \"origin=Debian,codename=${distro_codename}-security,label=Debian-Security\";\n",
                "    \"origin=Debian,codename=${distro_codename},label=Debian-Security\";\n",
                "};\n",
                "Unattended-Upgrade::AutoFixInterruptedDpkg \"true\";\n",
                "Unattended-Upgrade::MinimalSteps \"true\";\n",
                "Unattended-Upgrade::Remove-Unused-Kernel-Packages \"false\";\n",
                "Unattended-Upgrade::Remove-Unused-Dependencies \"false\";\n",
                "Unattended-Upgrade::Automatic-Reboot \"false\";\n",
            )
            .to_owned(),
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    const SIM: &str = "Reading package lists...\nThe following packages have been kept back:\n  linux-generic foo\nThe following packages will be upgraded:\n  libc6 curl\nInst libc6 [2.36-9] (2.36-9+deb12u7 Debian-Security:12/stable-security [amd64])\nInst curl [7.88] (7.88.1-10 Debian:12.5/stable [amd64])\nInst libnew (1.0 Debian:12/stable [amd64])\nRemv oldpkg [1.0]\nConf libc6 (2.36-9+deb12u7 Debian-Security:12/stable-security [amd64])\n";

    #[test]
    fn parses_simulation() {
        let sim = parse_simulation(SIM);
        assert_eq!(sim.upgrades.len(), 2);
        assert_eq!(sim.installs, vec!["libnew".to_owned()]);
        assert_eq!(sim.removals, vec!["oldpkg".to_owned()]);
        assert_eq!(
            sim.kept_back,
            vec!["linux-generic".to_owned(), "foo".to_owned()]
        );
        assert!(
            sim.upgrades
                .first()
                .is_some_and(|c| c.security && c.to == "2.36-9+deb12u7")
        );
        assert!(sim.upgrades.get(1).is_some_and(|c| !c.security));
    }

    #[test]
    fn rejects_hostile_names() {
        let sim = parse_simulation("Inst ;rm [1] (2 x)\nInst -y [1] (2 x)\nRemv $(x) [1]\n");
        assert_eq!(sim, AptSimulation::default());
        assert!(!valid_package_name(""));
        assert!(valid_package_name("libstdc++6"));
    }

    #[test]
    fn plan_orders_debian_before_nuxiva_and_flags_risk() {
        let plan = build_plan(&parse_simulation(SIM), true, "abc");
        let ids: Vec<&str> = plan.steps.iter().map(|s| s.id).collect();
        assert_eq!(ids, vec!["debian", "nuxiva"]);
        assert_eq!(plan.risk, "high");
        assert!(plan.needs_confirmation && plan.reboot_likely && !plan.steps.is_empty());
        assert_eq!(
            (plan.packages, plan.security, plan.removals, plan.kept_back),
            (3, 1, 1, 2)
        );
    }

    #[test]
    fn empty_plan_and_stable_id() {
        let plan = build_plan(&AptSimulation::default(), false, "");
        assert!(plan.steps.is_empty() && plan.risk == "low");
        let a = build_plan(&parse_simulation(SIM), true, "abc");
        let b = build_plan(&parse_simulation(SIM), true, "abc");
        let c = build_plan(&parse_simulation(SIM), true, "abd");
        assert_eq!(a.id, b.id);
        assert_ne!(a.id, c.id);
        assert_eq!(a.id.len(), 16);
    }

    #[test]
    fn auto_config_is_security_only_and_never_reboots() {
        let on = render_auto_config(true);
        assert!(
            on.iter()
                .any(|f| f.content.contains("Unattended-Upgrade \"1\""))
        );
        assert!(on.iter().all(|f| !f.content.contains("Reboot \"true\"")));
        let off = render_auto_config(false);
        assert!(
            off.iter()
                .any(|f| f.content.contains("Unattended-Upgrade \"0\""))
        );
    }
}
