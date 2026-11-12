use crate::numbers::{as_f64, round_to};

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CpuTimes {
    pub busy: u64,
    pub total: u64,
}

impl CpuTimes {
    #[must_use]
    pub fn percent_since(self, before: Self) -> f64 {
        let total = self.total.saturating_sub(before.total);
        let busy = self.busy.saturating_sub(before.busy);
        if total == 0 {
            return 0.0;
        }
        round_to(as_f64(busy.min(total)) / as_f64(total) * 100.0, 1)
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct MemInfo {
    pub total: u64,
    pub available: u64,
    pub swap_total: u64,
    pub swap_free: u64,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct NetTotals {
    pub rx: u64,
    pub tx: u64,
}

fn numbers(line: &str) -> Vec<u64> {
    line.split_whitespace()
        .filter_map(|v| v.parse().ok())
        .collect()
}

fn times(fields: &[u64]) -> CpuTimes {
    let get = |i: usize| fields.get(i).copied().unwrap_or_default();
    let total = fields
        .iter()
        .take(8)
        .fold(0u64, |acc, v| acc.saturating_add(*v));
    let idle = get(3).saturating_add(get(4));
    CpuTimes {
        busy: total.saturating_sub(idle),
        total,
    }
}

#[must_use]
pub fn parse_cpu_times(stat: &str) -> (CpuTimes, Vec<CpuTimes>, u64) {
    let mut all = CpuTimes::default();
    let mut cores = Vec::new();
    let mut boot = 0;
    for line in stat.lines() {
        let mut parts = line.splitn(2, char::is_whitespace);
        let label = parts.next().unwrap_or_default();
        let rest = parts.next().unwrap_or_default();
        if label == "cpu" {
            all = times(&numbers(rest));
        } else if label.starts_with("cpu")
            && label
                .get(3..)
                .is_some_and(|n| n.bytes().all(|b| b.is_ascii_digit()))
        {
            cores.push(times(&numbers(rest)));
        } else if label == "btime" {
            boot = numbers(rest).first().copied().unwrap_or_default();
        }
    }
    (all, cores, boot)
}

#[must_use]
pub fn parse_meminfo(text: &str) -> MemInfo {
    let mut info = MemInfo::default();
    let mut free = 0u64;
    let mut buffers = 0u64;
    let mut cached = 0u64;
    let mut has_available = false;
    for line in text.lines() {
        let Some((key, rest)) = line.split_once(':') else {
            continue;
        };
        let kib = numbers(rest).first().copied().unwrap_or_default();
        let bytes = kib.saturating_mul(1024);
        match key {
            "MemTotal" => info.total = bytes,
            "MemAvailable" => {
                info.available = bytes;
                has_available = true;
            }
            "MemFree" => free = bytes,
            "Buffers" => buffers = bytes,
            "Cached" => cached = bytes,
            "SwapTotal" => info.swap_total = bytes,
            "SwapFree" => info.swap_free = bytes,
            _ => {}
        }
    }
    if !has_available {
        info.available = free
            .saturating_add(buffers)
            .saturating_add(cached)
            .min(info.total);
    }
    info
}

#[must_use]
pub fn parse_loadavg(text: &str) -> [f64; 3] {
    let mut out = [0.0; 3];
    for (slot, value) in out.iter_mut().zip(text.split_whitespace()) {
        *slot = round_to(value.parse().unwrap_or(0.0), 2);
    }
    out
}

#[must_use]
pub fn parse_net_dev(text: &str) -> NetTotals {
    let mut totals = NetTotals::default();
    for line in text.lines().skip(2) {
        let Some((_, rest)) = line.split_once(':') else {
            continue;
        };
        let fields = numbers(rest);
        totals.rx = totals
            .rx
            .saturating_add(fields.first().copied().unwrap_or_default());
        totals.tx = totals
            .tx
            .saturating_add(fields.get(8).copied().unwrap_or_default());
    }
    totals
}
