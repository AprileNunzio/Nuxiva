#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchedulerError {
    UnknownInstance,
    InstanceId,
    TooManyWidgets,
    Cost,
}

impl SchedulerError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::UnknownInstance => "display.scheduler.unknown_instance",
            Self::InstanceId => "display.scheduler.instance_id",
            Self::TooManyWidgets => "display.scheduler.too_many_widgets",
            Self::Cost => "display.scheduler.cost",
        }
    }
}

impl std::fmt::Display for SchedulerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for SchedulerError {}
