use nuxiva_display_scheduler::WidgetInput;
use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const MAX_PLAN: usize = 256;

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Request {
    Ping {},
    Admit {
        screen: u16,
        widgets: Vec<WidgetInput>,
    },
    Visibility {
        instance: String,
        visible: bool,
    },
    Observe {
        instance: String,
        cost_mb: f32,
    },
    Error {
        instance: String,
    },
    Pressure {
        screen: u16,
        budget_mb: f32,
    },
    Audience {
        screen: u16,
        nucleus_only: bool,
    },
    Tick {},
    Status {
        screen: u16,
    },
    Diff {
        old: Value,
        new: Value,
    },
}

#[derive(Debug, Serialize)]
pub struct Response {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<&'static str>,
}

impl Response {
    #[must_use]
    pub const fn success(data: Value) -> Self {
        Self {
            ok: true,
            data: Some(data),
            error: None,
        }
    }

    #[must_use]
    pub const fn failure(code: &'static str) -> Self {
        Self {
            ok: false,
            data: None,
            error: Some(code),
        }
    }
}
