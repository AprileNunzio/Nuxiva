use serde::Serialize;

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct ProcessRow {
    pub pid: u32,
    pub name: String,
    pub cpu: f64,
    pub mem_mb: f64,
    pub status: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcessSample {
    pub pid: u32,
    pub name: String,
    pub state: char,
    pub ticks: u64,
    pub rss_pages: u64,
}

#[must_use]
pub fn status_name(state: char) -> &'static str {
    match state {
        'S' => "sleeping",
        'D' => "disk-sleep",
        'Z' => "zombie",
        'T' => "stopped",
        't' => "tracing-stop",
        'X' | 'x' => "dead",
        'I' => "idle",
        'P' => "parked",
        'W' => "waking",
        _ => "running",
    }
}

#[must_use]
pub fn parse_process_stat(text: &str) -> Option<ProcessSample> {
    let open = text.find('(')?;
    let close = text.rfind(')')?;
    if close <= open {
        return None;
    }
    let pid = text.get(..open)?.trim().parse().ok()?;
    let name = text.get(open.checked_add(1)?..close)?.to_owned();
    let rest: Vec<&str> = text
        .get(close.checked_add(1)?..)?
        .split_whitespace()
        .collect();
    let state = rest.first()?.chars().next()?;
    let utime: u64 = rest.get(11)?.parse().ok()?;
    let stime: u64 = rest.get(12)?.parse().ok()?;
    let rss_pages: u64 = rest.get(21)?.parse().unwrap_or(0);
    Some(ProcessSample {
        pid,
        name,
        state,
        ticks: utime.saturating_add(stime),
        rss_pages,
    })
}
