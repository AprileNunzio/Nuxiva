use model_router::Task;
use reason_eval::Verdict;
use reason_exec::{Report, Status};

use crate::signal::{Signal, StepOutcome};

fn outcome_of(status: &Status) -> StepOutcome {
    match status {
        Status::Done(_) => StepOutcome::Done,
        Status::Replayed(_) => StepOutcome::Replayed,
        Status::Failed => StepOutcome::Failed,
        Status::Denied => StepOutcome::Denied,
        Status::Indeterminate => StepOutcome::Indeterminate,
        Status::Missing => StepOutcome::Missing,
        Status::Skipped => StepOutcome::Skipped,
        Status::Cancelled => StepOutcome::Cancelled,
    }
}

#[must_use]
pub fn from_report(report: &Report) -> Vec<Signal> {
    report
        .steps
        .iter()
        .map(|step| Signal::Step {
            outcome: outcome_of(&step.status),
        })
        .collect()
}

#[must_use]
pub fn from_verdict(verdict: &Verdict, completed: bool) -> Signal {
    Signal::Intent {
        matched: verdict.intent_match && completed,
        completed,
        wrong_action: verdict.wrong_action,
    }
}

#[must_use]
pub fn task_of(name: &str) -> Option<Task> {
    match name {
        "understand" => Some(Task::Understand),
        "plan" => Some(Task::Plan),
        "summarize" => Some(Task::Summarize),
        "generate" => Some(Task::Generate),
        "code" => Some(Task::Code),
        "vision" => Some(Task::Vision),
        _ => None,
    }
}
