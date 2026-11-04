use agency_domain::{DomainError, TaskId};
use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum PlanError {
    #[error(transparent)]
    Domain(#[from] DomainError),
    #[error("task {0} already exists")]
    Duplicate(TaskId),
    #[error("task {task} depends on unknown task {missing}")]
    UnknownDependency { task: TaskId, missing: TaskId },
    #[error("task {0} not found")]
    NotFound(TaskId),
    #[error("the plan contains a dependency cycle")]
    Cycle,
    #[error("task {0} cannot be removed")]
    NotRemovable(TaskId),
    #[error("the plan exceeds {0} tasks")]
    TooLarge(usize),
}
