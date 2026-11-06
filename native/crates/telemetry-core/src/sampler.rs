use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::numbers::{as_f64, percent, round_to, to_u64};
use crate::process::{ProcessRow, ProcessSample, parse_process_stat, status_name};
use crate::procfs::{
    CpuTimes, NetTotals, parse_cpu_times, parse_loadavg, parse_meminfo, parse_net_dev,
};

const MAX_PROCESSES: usize = 32_768;
const MAX_FILE: u64 = 1 << 20;
const SENSORS: [&str; 4] = ["coretemp", "k10temp", "cpu_thermal", "acpitz"];

#[derive(Debug, Clone, PartialEq, Default, Serialize)]
pub struct Snapshot {
    pub uptime: u64,
    pub cpu_percent: f64,
    pub cpu_count: usize,
    pub cpu_freq: Option<f64>,
    pub per_cpu: Vec<f64>,
    pub load: [f64; 3],
    pub mem_total: u64,
    pub mem_used: u64,
    pub mem_percent: f64,
    pub swap_total: u64,
    pub swap_used: u64,
    pub swap_percent: f64,
    pub disk_total: u64,
    pub disk_used: u64,
    pub disk_percent: f64,
    pub net_rx_rate: u64,
    pub net_tx_rate: u64,
    pub temperature: Option<f64>,
    pub top_processes: Vec<ProcessRow>,
}

#[derive(Debug)]
pub struct Sampler {
    proc_root: PathBuf,
    sys_root: PathBuf,
    disk_path: PathBuf,
    cpu: Option<(CpuTimes, Vec<CpuTimes>)>,
    net: Option<(f64, NetTotals)>,
    processes: HashMap<u32, u64>,
    process_at: Option<f64>,
    ticks_per_second: f64,
    page_size: u64,
}

fn read(path: &Path) -> String {
    let Ok(meta) = fs::metadata(path) else {
        return String::new();
    };
    if meta.len() > MAX_FILE {
        return String::new();
    }
    fs::read_to_string(path).unwrap_or_default()
}

fn mean(values: &[f64]) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    let count = u64::try_from(values.len()).unwrap_or(u64::MAX);
    Some(values.iter().sum::<f64>() / as_f64(count))
}

impl Sampler {
    #[must_use]
    pub fn new(proc_root: PathBuf, sys_root: PathBuf, disk_path: PathBuf) -> Self {
        let ticks = rustix::param::clock_ticks_per_second();
        Self {
            proc_root,
            sys_root,
            disk_path,
            cpu: None,
            net: None,
            processes: HashMap::new(),
            process_at: None,
            ticks_per_second: if ticks == 0 { 100.0 } else { as_f64(ticks) },
            page_size: u64::try_from(rustix::param::page_size()).unwrap_or(4096),
        }
    }

    #[must_use]
    pub fn system() -> Self {
        Self::new(
            PathBuf::from("/proc"),
            PathBuf::from("/sys"),
            PathBuf::from("/"),
        )
    }

    fn cpu(&mut self, stat: &str) -> (f64, Vec<f64>, usize, u64) {
        let (all, cores, boot) = parse_cpu_times(stat);
        let (overall, per) = match &self.cpu {
            Some((before, before_cores)) => (
                all.percent_since(*before),
                cores
                    .iter()
                    .zip(
                        before_cores
                            .iter()
                            .chain(std::iter::repeat(&CpuTimes::default())),
                    )
                    .map(|(now, then)| now.percent_since(*then))
                    .collect(),
            ),
            None => (0.0, vec![0.0; cores.len()]),
        };
        let count = cores.len();
        self.cpu = Some((all, cores));
        (overall, per, count, boot)
    }

    fn net(&mut self, now: f64) -> (u64, u64) {
        let totals = parse_net_dev(&read(&self.proc_root.join("net/dev")));
        let rates = match self.net {
            Some((then, before)) if before.rx > 0 => {
                let dt = (now - then).max(0.001);
                let rate = |a: u64, b: u64| to_u64(as_f64(a.saturating_sub(b)) / dt);
                (rate(totals.rx, before.rx), rate(totals.tx, before.tx))
            }
            _ => (0, 0),
        };
        self.net = Some((now, totals));
        rates
    }

    fn disk(&self) -> (u64, u64, f64) {
        let Ok(stat) = rustix::fs::statvfs(&self.disk_path) else {
            return (0, 0, 0.0);
        };
        let frsize = stat.f_frsize;
        let total = stat.f_blocks.saturating_mul(frsize);
        let used = stat
            .f_blocks
            .saturating_sub(stat.f_bfree)
            .saturating_mul(frsize);
        let free = stat.f_bavail.saturating_mul(frsize);
        (total, used, percent(used, used.saturating_add(free)))
    }

    fn temperature(&self) -> Option<f64> {
        let mut found: HashMap<String, f64> = HashMap::new();
        let entries = fs::read_dir(self.sys_root.join("class/hwmon")).ok()?;
        for entry in entries.flatten().take(64) {
            let dir = entry.path();
            let name = read(&dir.join("name")).trim().to_owned();
            if !SENSORS.contains(&name.as_str()) {
                continue;
            }
            for index in 1..=64 {
                let raw = read(&dir.join(format!("temp{index}_input")));
                let Ok(milli) = raw.trim().parse::<i64>() else {
                    continue;
                };
                let celsius = f64::from(i32::try_from(milli).unwrap_or(0)) / 1000.0;
                let slot = found.entry(name.clone()).or_insert(f64::MIN);
                *slot = slot.max(celsius);
            }
        }
        SENSORS
            .iter()
            .find_map(|s| found.get(*s).copied())
            .map(|t| round_to(t, 1))
    }

    fn cpu_freq(&self) -> Option<f64> {
        let mut values = Vec::new();
        if let Ok(entries) = fs::read_dir(self.sys_root.join("devices/system/cpu")) {
            for entry in entries.flatten().take(4096) {
                let raw = read(&entry.path().join("cpufreq/scaling_cur_freq"));
                if let Ok(khz) = raw.trim().parse::<u64>() {
                    values.push(as_f64(khz) / 1000.0);
                }
            }
        }
        if values.is_empty() {
            for line in read(&self.proc_root.join("cpuinfo")).lines() {
                if let Some((key, value)) = line.split_once(':') {
                    if key.trim() == "cpu MHz" {
                        if let Ok(mhz) = value.trim().parse::<f64>() {
                            values.push(mhz);
                        }
                    }
                }
            }
        }
        mean(&values).map(|v| round_to(v, 1))
    }

    fn processes(&mut self, now: f64, limit: usize) -> Vec<ProcessRow> {
        let Ok(entries) = fs::read_dir(&self.proc_root) else {
            return Vec::new();
        };
        let elapsed = self.process_at.map(|then| (now - then).max(0.001));
        let mut seen = HashMap::new();
        let mut rows = Vec::new();
        for entry in entries.flatten().take(MAX_PROCESSES) {
            let file_name = entry.file_name();
            let Some(name) = file_name.to_str() else {
                continue;
            };
            if !name.bytes().all(|b| b.is_ascii_digit()) {
                continue;
            }
            let Some(sample) = parse_process_stat(&read(&entry.path().join("stat"))) else {
                continue;
            };
            let ProcessSample {
                pid,
                name,
                state,
                ticks,
                rss_pages,
            } = sample;
            seen.insert(pid, ticks);
            if name.is_empty()
                || matches!(name.to_lowercase().as_str(), "system idle process" | "idle")
            {
                continue;
            }
            let cpu = match (elapsed, self.processes.get(&pid)) {
                (Some(dt), Some(before)) => round_to(
                    as_f64(ticks.saturating_sub(*before)) / self.ticks_per_second / dt * 100.0,
                    1,
                ),
                _ => 0.0,
            };
            let mem = as_f64(rss_pages.saturating_mul(self.page_size)) / 1_048_576.0;
            rows.push(ProcessRow {
                pid,
                name,
                cpu,
                mem_mb: round_to(mem, 1),
                status: status_name(state).to_owned(),
            });
        }
        self.processes = seen;
        self.process_at = Some(now);
        rows.sort_by(|a, b| b.cpu.total_cmp(&a.cpu).then(b.mem_mb.total_cmp(&a.mem_mb)));
        rows.truncate(limit);
        rows
    }

    pub fn sample(&mut self, now: f64, limit: usize) -> Snapshot {
        let (cpu_percent, per_cpu, cpu_count, boot) = self.cpu(&read(&self.proc_root.join("stat")));
        let mem = parse_meminfo(&read(&self.proc_root.join("meminfo")));
        let mem_used = mem.total.saturating_sub(mem.available);
        let swap_used = mem.swap_total.saturating_sub(mem.swap_free);
        let (disk_total, disk_used, disk_percent) = self.disk();
        let (net_rx_rate, net_tx_rate) = self.net(now);
        let boot_f = as_f64(boot);
        Snapshot {
            uptime: if boot > 0 {
                to_u64((now - boot_f).floor())
            } else {
                0
            },
            cpu_percent,
            cpu_count,
            cpu_freq: self.cpu_freq(),
            per_cpu,
            load: parse_loadavg(&read(&self.proc_root.join("loadavg"))),
            mem_total: mem.total,
            mem_used,
            mem_percent: percent(mem_used, mem.total),
            swap_total: mem.swap_total,
            swap_used,
            swap_percent: percent(swap_used, mem.swap_total),
            disk_total,
            disk_used,
            disk_percent,
            net_rx_rate,
            net_tx_rate,
            temperature: self.temperature(),
            top_processes: self.processes(now, limit),
        }
    }
}
