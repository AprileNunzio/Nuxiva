use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};
use crate::stats::{Summary, ratio, round6, summarize, u64_f64};

pub const MAX_WORDS: usize = 1_024;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Ops {
    pub substitutions: u32,
    pub deletions: u32,
    pub insertions: u32,
}

impl Ops {
    #[must_use]
    pub fn errors(&self) -> u64 {
        u64::from(self.substitutions)
            .saturating_add(u64::from(self.deletions))
            .saturating_add(u64::from(self.insertions))
    }
}

#[derive(Debug, Clone, Copy, Default)]
struct Cell {
    cost: u32,
    ops: Ops,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WerReport {
    pub utterances: u64,
    pub reference_words: u64,
    pub substitutions: u64,
    pub deletions: u64,
    pub insertions: u64,
    pub errors: u64,
    pub wer: f64,
    pub utterance_error_rate: f64,
    pub utterance_wer: Summary,
}

#[must_use]
pub fn tokens(text: &str) -> Vec<String> {
    text.to_lowercase()
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { ' ' })
        .collect::<String>()
        .split_whitespace()
        .map(str::to_owned)
        .collect()
}

fn step(from: Cell, ops: Ops) -> Cell {
    Cell {
        cost: from.cost.saturating_add(1),
        ops,
    }
}

#[must_use]
pub fn align(reference: &[String], hypothesis: &[String]) -> Ops {
    let width = u32::try_from(hypothesis.len()).unwrap_or(u32::MAX);
    let mut previous: Vec<Cell> = (0..=width)
        .map(|j| Cell {
            cost: j,
            ops: Ops {
                insertions: j,
                ..Ops::default()
            },
        })
        .collect();
    for (i, r) in reference.iter().enumerate() {
        let row = u32::try_from(i).unwrap_or(u32::MAX).saturating_add(1);
        let mut current = Vec::with_capacity(previous.len());
        current.push(Cell {
            cost: row,
            ops: Ops {
                deletions: row,
                ..Ops::default()
            },
        });
        for (j, h) in hypothesis.iter().enumerate() {
            let diagonal = previous.get(j).copied().unwrap_or_default();
            let up = previous
                .get(j.saturating_add(1))
                .copied()
                .unwrap_or_default();
            let left = current.last().copied().unwrap_or_default();
            let substitute = if r == h {
                diagonal
            } else {
                step(
                    diagonal,
                    Ops {
                        substitutions: diagonal.ops.substitutions.saturating_add(1),
                        ..diagonal.ops
                    },
                )
            };
            let delete = step(
                up,
                Ops {
                    deletions: up.ops.deletions.saturating_add(1),
                    ..up.ops
                },
            );
            let insert = step(
                left,
                Ops {
                    insertions: left.ops.insertions.saturating_add(1),
                    ..left.ops
                },
            );
            let mut best = substitute;
            if delete.cost < best.cost {
                best = delete;
            }
            if insert.cost < best.cost {
                best = insert;
            }
            current.push(best);
        }
        previous = current;
    }
    previous.last().map(|c| c.ops).unwrap_or_default()
}

pub fn analyze<'a, I>(pairs: I) -> BenchResult<WerReport>
where
    I: IntoIterator<Item = (&'a str, &'a str)>,
{
    let mut report = WerReport::default();
    let mut failing = 0u64;
    let mut per_utterance = Vec::new();
    for (reference, hypothesis) in pairs {
        let r = tokens(reference);
        let h = tokens(hypothesis);
        if r.is_empty() {
            return Err(BenchError::Invalid("reference_empty"));
        }
        if r.len() > MAX_WORDS || h.len() > MAX_WORDS {
            return Err(BenchError::TooLarge("words"));
        }
        let ops = align(&r, &h);
        let words = u64::try_from(r.len()).unwrap_or(u64::MAX);
        report.utterances = report.utterances.saturating_add(1);
        report.reference_words = report.reference_words.saturating_add(words);
        report.substitutions = report
            .substitutions
            .saturating_add(u64::from(ops.substitutions));
        report.deletions = report.deletions.saturating_add(u64::from(ops.deletions));
        report.insertions = report.insertions.saturating_add(u64::from(ops.insertions));
        if ops.errors() > 0 {
            failing = failing.saturating_add(1);
        }
        per_utterance.push(round6(u64_f64(ops.errors()) / u64_f64(words)));
    }
    report.errors = report
        .substitutions
        .saturating_add(report.deletions)
        .saturating_add(report.insertions);
    report.wer = ratio(report.errors, report.reference_words);
    report.utterance_error_rate = ratio(failing, report.utterances);
    report.utterance_wer = summarize(&per_utterance)?;
    Ok(report)
}
