use serde::{Deserialize, Serialize};

use crate::kind::{Kind, Level};
use crate::store::Report;

#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Facts {
    pub steps_total: u32,
    pub steps_failed: u32,
    pub outcome_status: String,
    pub outcome_verified: bool,
    pub answer_empty: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Check {
    pub id: &'static str,
    pub ok: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Superata,
    NonSuperata,
    Incompleta,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Judgement {
    pub verdict: Verdict,
    pub checks: Vec<Check>,
}

const BAD_STATUS: [&str; 4] = ["failed", "blocked", "cancelled", "error"];

#[must_use]
pub fn judge(report: &Report, facts: &Facts) -> Judgement {
    let level = Level::parse(&report.level);
    let files = level.is_some_and(|l| {
        l.required()
            .iter()
            .filter(|k| **k != Kind::Verifica)
            .all(|k| report.files.iter().any(|f| Kind::of_name(f) == Some(*k)))
    });
    let chain = report.ok;
    let steps = facts.steps_failed == 0;
    let status_bad = BAD_STATUS.contains(&facts.outcome_status.as_str());
    let outcome = facts.outcome_verified && !status_bad;
    let answer = !facts.answer_empty;
    let checks = vec![
        Check {
            id: "chain",
            ok: chain,
        },
        Check {
            id: "files",
            ok: files,
        },
        Check {
            id: "steps",
            ok: steps,
        },
        Check {
            id: "outcome",
            ok: outcome,
        },
        Check {
            id: "answer",
            ok: answer,
        },
    ];
    let verdict = if !chain || !steps || status_bad {
        Verdict::NonSuperata
    } else if !files || !outcome || !answer {
        Verdict::Incompleta
    } else {
        Verdict::Superata
    };
    Judgement { verdict, checks }
}
