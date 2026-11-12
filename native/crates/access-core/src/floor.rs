use crate::cell::Cell;
use crate::role::COLUMNS;

const OUTSIDER_DENY: [&str; 16] = [
    "home.lock.unlock",
    "home.alarm.disarm",
    "home.gate.open",
    "home.valve.set",
    "home.camera.",
    "home.automation.",
    "home.private.",
    "home.system.",
    "comm.",
    "commerce.",
    "system.",
    "sentinel.",
    "people.",
    "memory.",
    "files.",
    "risk.critical",
];
const STRONG_FOR_ALL: [&str; 6] = [
    "home.lock.unlock",
    "home.alarm.disarm",
    "home.valve.set",
    "commerce.",
    "system.admin.",
    "sentinel.",
];
const GUEST: usize = 4;
const ANONYMOUS: usize = 5;

fn covered(pattern: &str, list: &[&str]) -> bool {
    let bare = pattern.trim_end_matches('*');
    list.iter().any(|p| {
        if p.ends_with('.') {
            bare.starts_with(p) || p.starts_with(bare)
        } else {
            bare == *p || p.starts_with(bare)
        }
    })
}

#[must_use]
pub fn floor(pattern: &str) -> [Cell; COLUMNS] {
    let mut cells = [Cell::Allow; COLUMNS];
    if covered(pattern, &STRONG_FOR_ALL) {
        cells = [Cell::Strong; COLUMNS];
    }
    if covered(pattern, &OUTSIDER_DENY) {
        for column in [GUEST, ANONYMOUS] {
            if let Some(cell) = cells.get_mut(column) {
                *cell = Cell::Deny;
            }
        }
    }
    cells
}

#[must_use]
pub fn harden(pattern: &str, cells: [Cell; COLUMNS]) -> [Cell; COLUMNS] {
    let base = floor(pattern);
    let mut out = cells;
    for (cell, min) in out.iter_mut().zip(base) {
        *cell = (*cell).max(min);
    }
    out
}
