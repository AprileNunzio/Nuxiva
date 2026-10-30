use agency_domain::TaskSpec;
use agency_scheduler::{ModelProfile, Settings};
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BudgetInput {
    pub tokens: u64,
    pub seconds: u64,
    pub parallel: u16,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Control {
    Pause,
    Resume,
    Cancel,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskAction {
    Submit,
    Approve,
    Rework,
    Fail,
    Cancel,
    Interrupt,
}

impl TaskAction {
    #[must_use]
    pub fn event(self) -> &'static str {
        match self {
            Self::Submit => "task.submitted",
            Self::Approve => "task.approved",
            Self::Rework => "task.rework",
            Self::Fail => "task.failed",
            Self::Cancel => "task.cancelled",
            Self::Interrupt => "task.interrupted",
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Request {
    Ping {},
    Capacity {},
    SettingsGet {},
    SettingsSet {
        scheduler: Settings,
        model: ModelProfile,
    },
    ProjectCreate {
        id: String,
        title: String,
        goal: String,
        workspace: String,
        budget: BudgetInput,
    },
    ProjectList {},
    ProjectGet {
        id: String,
    },
    ProjectPlan {
        id: String,
        tasks: Vec<TaskSpec>,
    },
    ProjectControl {
        id: String,
        action: Control,
    },
    TaskUpdate {
        project: String,
        task: String,
        action: TaskAction,
        #[serde(default)]
        feedback: Option<String>,
        #[serde(default)]
        tokens: u64,
        #[serde(default)]
        seconds: u64,
    },
    Dispatch {},
}

#[derive(Debug, Serialize)]
pub struct Response {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ErrorBody>,
}

#[derive(Debug, Serialize)]
pub struct ErrorBody {
    pub code: &'static str,
    pub message: String,
}

impl Response {
    #[must_use]
    pub fn success(data: Value) -> Self {
        Self {
            ok: true,
            data: Some(data),
            error: None,
        }
    }

    #[must_use]
    pub fn failure(code: &'static str, message: String) -> Self {
        Self {
            ok: false,
            data: None,
            error: Some(ErrorBody { code, message }),
        }
    }
}
