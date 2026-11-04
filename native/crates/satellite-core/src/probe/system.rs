use serde::Serialize;

use super::root::{Root, clean_label};

const FEATURES: &[(&str, &str)] = &[
    ("avx2", "avx2"),
    ("avx512f", "avx512"),
    ("avx_vnni", "avx-vnni"),
    ("amx_tile", "amx"),
    ("asimd", "neon"),
    ("neon", "neon"),
    ("asimddp", "dotprod"),
    ("i8mm", "i8mm"),
    ("fphp", "fp16"),
    ("sve", "sve"),
    ("sve2", "sve2"),
];

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct System {
    pub hostname: String,
    pub arch: String,
    pub cores: u32,
    pub ram_mb: u32,
    pub disk_gb: u32,
    pub os: String,
    pub kernel: String,
    pub model: String,
    pub cpu_features: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Metrics {
    pub cpu: f64,
    pub ram: f64,
    pub disk: f64,
    pub uptime: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temp: Option<f64>,
}

#[must_use]
pub fn system(root: &Root) -> System {
    let disk = disk_space(root);
    System {
        hostname: root
            .read_trim("/proc/sys/kernel/hostname")
            .map(|h| clean_label(&h, 60))
            .unwrap_or_default(),
        arch: std::env::consts::ARCH.to_owned(),
        cores: cores(root),
        ram_mb: mb(meminfo(root, "MemTotal")),
        disk_gb: u32::try_from(disk.0 >> 30).unwrap_or(u32::MAX),
        os: os_name(root),
        kernel: root
            .read_trim("/proc/sys/kernel/osrelease")
            .map(|k| clean_label(&k, 60))
            .unwrap_or_default(),
        model: model(root),
        cpu_features: cpu_features(root),
    }
}

#[must_use]
pub fn metrics(root: &Root, cores: u32) -> Metrics {
    let load = root
        .read("/proc/loadavg")
        .and_then(|text| {
            text.split_whitespace()
                .next()
                .and_then(|v| v.parse::<f64>().ok())
        })
        .unwrap_or(0.0);
    let total = f64::from(mb(meminfo(root, "MemTotal")));
    let available = f64::from(mb(meminfo(root, "MemAvailable")));
    let (disk_total, disk_free) = disk_space(root);
    Metrics {
        cpu: round1((load * 100.0 / f64::from(cores.max(1))).min(100.0)),
        ram: round1(percent(total - available, total)),
        disk: round1(percent(
            gib(disk_total.saturating_sub(disk_free)),
            gib(disk_total),
        )),
        uptime: root
            .read("/proc/uptime")
            .and_then(|text| {
                text.split_whitespace()
                    .next()
                    .and_then(|v| v.parse::<f64>().ok())
            })
            .unwrap_or(0.0),
        temp: temperature(root),
    }
}

fn cores(root: &Root) -> u32 {
    let listed = root.read("/proc/cpuinfo").map_or(0, |text| {
        text.lines().filter(|l| l.starts_with("processor")).count()
    });
    let counted = if listed == 0 {
        std::thread::available_parallelism().map_or(1, std::num::NonZero::get)
    } else {
        listed
    };
    u32::try_from(counted).unwrap_or(u32::MAX).clamp(1, 4096)
}

fn meminfo(root: &Root, key: &str) -> u64 {
    root.read("/proc/meminfo")
        .and_then(|text| {
            text.lines().find_map(|line| {
                let (name, value) = line.split_once(':')?;
                (name == key).then(|| value.split_whitespace().next()?.parse::<u64>().ok())?
            })
        })
        .unwrap_or(0)
}

fn mb(kb: u64) -> u32 {
    u32::try_from(kb >> 10).unwrap_or(u32::MAX)
}

fn gib(bytes: u64) -> f64 {
    f64::from(u32::try_from(bytes >> 20).unwrap_or(u32::MAX))
}

fn percent(part: f64, whole: f64) -> f64 {
    if whole <= 0.0 {
        0.0
    } else {
        (part * 100.0 / whole).clamp(0.0, 100.0)
    }
}

fn round1(value: f64) -> f64 {
    (value * 10.0).round() / 10.0
}

fn disk_space(root: &Root) -> (u64, u64) {
    rustix::fs::statvfs(root.base()).map_or((0, 0), |stat| {
        (
            stat.f_blocks.saturating_mul(stat.f_frsize),
            stat.f_bavail.saturating_mul(stat.f_frsize),
        )
    })
}

fn os_name(root: &Root) -> String {
    root.read("/etc/os-release")
        .and_then(|text| {
            text.lines()
                .find_map(|line| line.strip_prefix("PRETTY_NAME="))
                .map(|value| clean_label(value.trim_matches('"'), 60))
        })
        .unwrap_or_default()
}

fn model(root: &Root) -> String {
    let tree = root
        .read_trim("/proc/device-tree/model")
        .or_else(|| root.read_trim("/sys/firmware/devicetree/base/model"));
    if let Some(name) = tree {
        return clean_label(&name, 80);
    }
    let vendor = root
        .read_trim("/sys/class/dmi/id/sys_vendor")
        .unwrap_or_default();
    let product = root
        .read_trim("/sys/class/dmi/id/product_name")
        .unwrap_or_default();
    clean_label(&format!("{vendor} {product}"), 80)
}

fn cpu_features(root: &Root) -> Vec<String> {
    let text = root.read("/proc/cpuinfo").unwrap_or_default();
    let mut found: Vec<String> = Vec::new();
    for line in text.lines() {
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        let key = key.trim();
        if key == "flags" || key == "Features" {
            for flag in value.split_whitespace() {
                if let Some((_, name)) = FEATURES.iter().find(|(raw, _)| *raw == flag) {
                    found.push((*name).to_owned());
                }
            }
        } else if key == "isa" && riscv_vector(value) {
            found.push("rvv".to_owned());
        }
    }
    found.sort();
    found.dedup();
    found
}

fn riscv_vector(isa: &str) -> bool {
    let isa = isa.trim();
    let base = isa.split('_').next().unwrap_or_default();
    base.strip_prefix("rv64")
        .or_else(|| base.strip_prefix("rv32"))
        .is_some_and(|letters| letters.contains('v'))
        || isa
            .split('_')
            .any(|ext| ext.starts_with("zve") || ext == "v")
}

fn temperature(root: &Root) -> Option<f64> {
    root.entries("/sys/class/thermal")
        .iter()
        .filter(|name| name.starts_with("thermal_zone"))
        .filter_map(|zone| root.read_trim(&format!("/sys/class/thermal/{zone}/temp")))
        .filter_map(|raw| raw.parse::<i32>().ok())
        .map(|milli| f64::from(milli) / 1000.0)
        .filter(|celsius| (-40.0..150.0).contains(celsius))
        .reduce(f64::max)
        .map(round1)
}
