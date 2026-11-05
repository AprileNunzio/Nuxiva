use serde::{Deserialize, Serialize};
use std::fmt;

pub const STAGES: [(&str, u32); 9] = [
    ("check", 5),
    ("fetch", 15),
    ("verify_ci", 10),
    ("verify_signature", 10),
    ("snapshot", 5),
    ("apply", 20),
    ("integrity", 15),
    ("restart", 10),
    ("confirm", 10),
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StageStatus {
    Pending,
    Running,
    Done,
    Skipped,
    Failed,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Stage {
    pub id: String,
    pub weight: u32,
    pub status: StageStatus,
    pub started_at: Option<f64>,
    pub finished_at: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Pipeline {
    pub stages: Vec<Stage>,
    pub percent: u32,
    pub active: Option<String>,
    pub outcome: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PipelineError {
    UnknownStage,
    Terminal,
    Regression,
    InvalidTransition,
}

impl fmt::Display for PipelineError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::UnknownStage => "unknown_stage",
            Self::Terminal => "pipeline_terminal",
            Self::Regression => "stage_regression",
            Self::InvalidTransition => "invalid_transition",
        })
    }
}

impl std::error::Error for PipelineError {}

impl Default for Pipeline {
    fn default() -> Self {
        let stages = STAGES
            .iter()
            .map(|(id, weight)| Stage {
                id: (*id).to_owned(),
                weight: *weight,
                status: StageStatus::Pending,
                started_at: None,
                finished_at: None,
            })
            .collect();
        Self {
            stages,
            percent: 0,
            active: None,
            outcome: None,
        }
    }
}

impl Pipeline {
    fn index(&self, id: &str) -> Result<usize, PipelineError> {
        self.stages
            .iter()
            .position(|s| s.id == id)
            .ok_or(PipelineError::UnknownStage)
    }

    fn recompute(&mut self) {
        let total: u32 = self
            .stages
            .iter()
            .map(|s| s.weight)
            .fold(0, u32::saturating_add);
        let earned: u32 = self
            .stages
            .iter()
            .map(|s| match s.status {
                StageStatus::Done | StageStatus::Skipped => s.weight.saturating_mul(2),
                StageStatus::Running => s.weight,
                _ => 0,
            })
            .fold(0, u32::saturating_add);
        self.percent = earned
            .saturating_mul(50)
            .checked_div(total)
            .unwrap_or(0)
            .min(100);
        self.active = self
            .stages
            .iter()
            .find(|s| s.status == StageStatus::Running)
            .map(|s| s.id.clone());
        let all_closed = self
            .stages
            .iter()
            .all(|s| matches!(s.status, StageStatus::Done | StageStatus::Skipped));
        if self.stages.iter().any(|s| s.status == StageStatus::Failed) {
            self.outcome = Some(String::from("failed"));
        } else if all_closed {
            self.outcome = Some(String::from("success"));
        }
    }

    pub fn advance(
        &mut self,
        id: &str,
        status: StageStatus,
        now: f64,
    ) -> Result<(), PipelineError> {
        if self.outcome.is_some() {
            return Err(PipelineError::Terminal);
        }
        let at = self.index(id)?;
        let later_started = self
            .stages
            .iter()
            .skip(at.saturating_add(1))
            .any(|s| s.status != StageStatus::Pending);
        if later_started {
            return Err(PipelineError::Regression);
        }
        let current = self
            .stages
            .get(at)
            .map(|s| s.status)
            .ok_or(PipelineError::UnknownStage)?;
        let allowed = matches!(
            (current, status),
            (
                StageStatus::Pending,
                StageStatus::Running
                    | StageStatus::Done
                    | StageStatus::Skipped
                    | StageStatus::Failed
            ) | (
                StageStatus::Running,
                StageStatus::Done | StageStatus::Failed | StageStatus::Skipped
            )
        );
        if !allowed {
            return Err(PipelineError::InvalidTransition);
        }
        for earlier in self.stages.iter_mut().take(at) {
            match earlier.status {
                StageStatus::Pending => {
                    earlier.status = StageStatus::Skipped;
                    earlier.finished_at = Some(now);
                }
                StageStatus::Running => {
                    earlier.status = StageStatus::Done;
                    earlier.finished_at = Some(now);
                }
                _ => {}
            }
        }
        if let Some(stage) = self.stages.get_mut(at) {
            if stage.started_at.is_none() {
                stage.started_at = Some(now);
            }
            if status != StageStatus::Running {
                stage.finished_at = Some(now);
            }
            stage.status = status;
        }
        self.recompute();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn runs_forward_and_reaches_full_percent() {
        let mut p = Pipeline::default();
        for (id, _) in STAGES {
            assert!(p.advance(id, StageStatus::Running, 1.0).is_ok());
            assert!(p.advance(id, StageStatus::Done, 2.0).is_ok());
        }
        assert_eq!(p.percent, 100);
        assert_eq!(p.outcome.as_deref(), Some("success"));
        assert_eq!(
            p.advance("check", StageStatus::Running, 3.0),
            Err(PipelineError::Terminal)
        );
    }

    #[test]
    fn skips_earlier_and_rejects_regression() {
        let mut p = Pipeline::default();
        assert!(p.advance("apply", StageStatus::Running, 1.0).is_ok());
        assert_eq!(
            p.stages.first().map(|s| s.status),
            Some(StageStatus::Skipped)
        );
        assert_eq!(p.active.as_deref(), Some("apply"));
        assert_eq!(
            p.advance("fetch", StageStatus::Running, 2.0),
            Err(PipelineError::Regression)
        );
        assert_eq!(
            p.advance("nope", StageStatus::Running, 2.0),
            Err(PipelineError::UnknownStage)
        );
        assert!(p.advance("apply", StageStatus::Failed, 2.0).is_ok());
        assert_eq!(p.outcome.as_deref(), Some("failed"));
    }

    #[test]
    fn rejects_invalid_transition() {
        let mut p = Pipeline::default();
        assert!(p.advance("check", StageStatus::Done, 1.0).is_ok());
        assert_eq!(
            p.advance("check", StageStatus::Running, 1.0),
            Err(PipelineError::InvalidTransition)
        );
    }
}
