#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Status {
    Done(String),
    Replayed(String),
    Failed,
    Denied,
    Indeterminate,
    Missing,
    Skipped,
    Cancelled,
}

impl Status {
    #[must_use]
    pub fn output(&self) -> Option<&str> {
        match self {
            Self::Done(out) | Self::Replayed(out) => Some(out),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StepReport {
    pub step: String,
    pub status: Status,
    pub attempts: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Report {
    pub steps: Vec<StepReport>,
}

impl Report {
    #[must_use]
    pub fn get(&self, step: &str) -> Option<&StepReport> {
        self.steps.iter().find(|s| s.step == step)
    }

    #[must_use]
    pub fn complete(&self) -> bool {
        self.steps
            .iter()
            .all(|s| matches!(s.status, Status::Done(_) | Status::Replayed(_)))
    }

    #[must_use]
    pub fn needs_human(&self) -> Vec<&str> {
        self.steps
            .iter()
            .filter(|s| matches!(s.status, Status::Indeterminate | Status::Denied))
            .map(|s| s.step.as_str())
            .collect()
    }
}
