use crate::text::has_control;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

pub const MAX_MANIFEST_BYTES: usize = 64 * 1024;
pub const MAX_ID: usize = 40;
pub const MAX_NAME: usize = 80;
pub const MAX_DESCRIPTION: usize = 1_200;
pub const MAX_ITEM: usize = 400;
pub const MAX_LIST: usize = 64;
pub const MAX_ROUTING: usize = 160;
pub const MAX_RAM_MB: u64 = 1_048_576;

pub const CATEGORIES: &[&str] = &[
    "creativita",
    "percezione",
    "cognizione",
    "sicurezza",
    "domotica",
    "infrastruttura",
    "multimedia",
    "comunicazione",
    "conoscenza",
    "salute",
    "sport",
    "scienza",
    "informatica",
];

pub const LEGACY_CATEGORIES: &[&str] = &[
    "assistente",
    "casa",
    "home",
    "intrattenimento",
    "intelligenza",
    "sistema",
    "altro",
];

pub const RESERVED_IDS: &[&str] = &[
    "agenti", "features", "registry", "loader", "schema", "scaffold", "core", "category",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    Error,
    Warning,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Issue {
    pub field: String,
    pub code: String,
    pub severity: Severity,
}

impl Issue {
    fn error(field: &str, code: &str) -> Self {
        Self {
            field: field.to_owned(),
            code: code.to_owned(),
            severity: Severity::Error,
        }
    }

    fn warning(field: &str, code: &str) -> Self {
        Self {
            field: field.to_owned(),
            code: code.to_owned(),
            severity: Severity::Warning,
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Routing {
    pub nouns: Vec<String>,
    pub phrases: Vec<String>,
    pub verbs: Vec<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Profile {
    pub ram_mb: u64,
    pub vram_mb: u64,
    pub heavy: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Manifest {
    pub id: String,
    pub name: String,
    pub icon: String,
    pub category: String,
    pub description: String,
    pub capabilities: Vec<String>,
    pub routing: Routing,
    pub profile: Profile,
    pub tools: Vec<String>,
    pub skills: Vec<String>,
    pub widgets: Vec<String>,
    pub api: String,
    pub source: String,
    pub version: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Report {
    pub manifest: Option<Manifest>,
    pub issues: Vec<Issue>,
}

impl Report {
    #[must_use]
    pub fn is_valid(&self) -> bool {
        self.manifest.is_some()
    }
}

#[must_use]
pub fn valid_id(id: &str) -> bool {
    let mut chars = id.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    let len = id.chars().count();
    first.is_ascii_lowercase()
        && (2..=MAX_ID).contains(&len)
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_')
}

#[must_use]
pub fn valid_folder(name: &str) -> bool {
    let mut chars = name.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    let len = name.chars().count();
    (first.is_ascii_lowercase() || first.is_ascii_digit())
        && (2..=41).contains(&len)
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || c == '-')
}

#[must_use]
pub fn known_category(category: &str) -> bool {
    CATEGORIES.contains(&category)
}

fn text(obj: &Map<String, Value>, key: &str, limit: usize, issues: &mut Vec<Issue>) -> String {
    match obj.get(key) {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(s)) => {
            let trimmed = s.trim();
            if has_control(trimmed) {
                issues.push(Issue::error(key, "control_chars"));
                String::new()
            } else if trimmed.chars().count() > limit {
                issues.push(Issue::error(key, "too_long"));
                String::new()
            } else {
                trimmed.to_owned()
            }
        }
        Some(_) => {
            issues.push(Issue::error(key, "type_string"));
            String::new()
        }
    }
}

fn list_item(value: &Value) -> Option<String> {
    match value {
        Value::String(s) => Some(s.trim().to_owned()),
        Value::Object(o) => o
            .get("name")
            .or_else(|| o.get("id"))
            .and_then(Value::as_str)
            .map(|s| s.trim().to_owned()),
        _ => None,
    }
}

fn list(value: Option<&Value>, field: &str, max: usize, issues: &mut Vec<Issue>) -> Vec<String> {
    let Some(raw) = value else { return Vec::new() };
    if raw.is_null() {
        return Vec::new();
    }
    let Some(items) = raw.as_array() else {
        issues.push(Issue::error(field, "type_list"));
        return Vec::new();
    };
    if items.len() > max {
        issues.push(Issue::error(field, "too_many"));
        return Vec::new();
    }
    let mut out: Vec<String> = Vec::with_capacity(items.len());
    for item in items {
        let Some(s) = list_item(item) else {
            issues.push(Issue::error(field, "type_item"));
            continue;
        };
        if s.is_empty() {
            continue;
        }
        if has_control(&s) {
            issues.push(Issue::error(field, "control_chars"));
        } else if s.chars().count() > MAX_ITEM {
            issues.push(Issue::error(field, "too_long"));
        } else if !out.contains(&s) {
            out.push(s);
        }
    }
    out
}

fn megabytes(value: Option<&Value>, scale: f64, field: &str, issues: &mut Vec<Issue>) -> u64 {
    let Some(raw) = value else { return 0 };
    if raw.is_null() {
        return 0;
    }
    let Some(number) = raw.as_f64() else {
        issues.push(Issue::error(field, "type_number"));
        return 0;
    };
    let scaled = number * scale;
    if !scaled.is_finite() || scaled < 0.0 || scaled > 1_048_576.0 {
        issues.push(Issue::error(field, "out_of_range"));
        return 0;
    }
    format!("{scaled:.0}")
        .parse::<u64>()
        .unwrap_or(0)
        .min(MAX_RAM_MB)
}

fn profile(obj: &Map<String, Value>, issues: &mut Vec<Issue>) -> Profile {
    if let Some(raw) = obj.get("profile").filter(|v| !v.is_null()) {
        let Some(p) = raw.as_object() else {
            issues.push(Issue::error("profile", "type_object"));
            return Profile::default();
        };
        let heavy = match p.get("heavy") {
            None | Some(Value::Null) => false,
            Some(Value::Bool(b)) => *b,
            Some(_) => {
                issues.push(Issue::error("profile.heavy", "type_bool"));
                false
            }
        };
        return Profile {
            ram_mb: megabytes(p.get("ram_mb"), 1.0, "profile.ram_mb", issues),
            vram_mb: megabytes(p.get("vram_mb"), 1.0, "profile.vram_mb", issues),
            heavy,
        };
    }
    let Some(req) = obj.get("requires").and_then(Value::as_object) else {
        return Profile::default();
    };
    Profile {
        ram_mb: megabytes(req.get("ram_gb"), 1024.0, "requires.ram_gb", issues),
        vram_mb: megabytes(
            req.get("gpu_vram_gb"),
            1024.0,
            "requires.gpu_vram_gb",
            issues,
        ),
        heavy: false,
    }
}

fn routing(obj: &Map<String, Value>, issues: &mut Vec<Issue>) -> Routing {
    let Some(raw) = obj.get("routing").filter(|v| !v.is_null()) else {
        return Routing::default();
    };
    let Some(r) = raw.as_object() else {
        issues.push(Issue::error("routing", "type_object"));
        return Routing::default();
    };
    Routing {
        nouns: list(r.get("nouns"), "routing.nouns", MAX_ROUTING, issues),
        phrases: list(r.get("phrases"), "routing.phrases", MAX_ROUTING, issues),
        verbs: list(r.get("verbs"), "routing.verbs", MAX_ROUTING, issues),
    }
}

fn identity(obj: &Map<String, Value>, folder: &str, issues: &mut Vec<Issue>) -> String {
    let id = match obj.get("id") {
        None | Some(Value::Null) => folder.to_owned(),
        Some(Value::String(s)) => s.trim().to_owned(),
        Some(_) => {
            issues.push(Issue::error("id", "type_string"));
            return String::new();
        }
    };
    if !valid_id(&id) {
        issues.push(Issue::error("id", "id_invalid"));
    } else if RESERVED_IDS.contains(&id.as_str()) {
        issues.push(Issue::error("id", "id_reserved"));
    } else if !folder.is_empty() && id != folder {
        issues.push(Issue::warning("id", "id_folder_mismatch"));
    }
    id
}

fn category(
    obj: &Map<String, Value>,
    folder_category: Option<&str>,
    issues: &mut Vec<Issue>,
) -> String {
    let declared = text(obj, "category", 40, issues);
    if let Some(physical) = folder_category {
        if known_category(&declared) && declared != physical {
            issues.push(Issue::warning("category", "category_folder_mismatch"));
        }
        if !known_category(physical) {
            issues.push(Issue::warning("category", "category_unknown"));
        }
        return physical.to_owned();
    }
    if declared.is_empty() {
        issues.push(Issue::warning("category", "category_missing"));
        return "altro".to_owned();
    }
    if !known_category(&declared) {
        let code = if LEGACY_CATEGORIES.contains(&declared.as_str()) {
            "category_legacy"
        } else {
            "category_unknown"
        };
        issues.push(Issue::warning("category", code));
    }
    declared
}

#[must_use]
pub fn validate_value(raw: &Value, folder: &str, folder_category: Option<&str>) -> Report {
    let mut issues = Vec::new();
    let Some(obj) = raw.as_object() else {
        return Report {
            manifest: None,
            issues: vec![Issue::error("", "not_object")],
        };
    };
    let id = identity(obj, folder, &mut issues);
    let name = text(obj, "name", MAX_NAME, &mut issues);
    if name.is_empty() {
        issues.push(Issue::error("name", "name_missing"));
    }
    let manifest = Manifest {
        id,
        name,
        icon: text(obj, "icon", 16, &mut issues),
        category: category(obj, folder_category, &mut issues),
        description: text(obj, "description", MAX_DESCRIPTION, &mut issues),
        capabilities: list(
            obj.get("capabilities"),
            "capabilities",
            MAX_LIST,
            &mut issues,
        ),
        routing: routing(obj, &mut issues),
        profile: profile(obj, &mut issues),
        tools: list(obj.get("tools"), "tools", MAX_LIST, &mut issues),
        skills: list(obj.get("skills"), "skills", MAX_LIST, &mut issues),
        widgets: list(obj.get("widgets"), "widgets", MAX_LIST, &mut issues),
        api: text(obj, "api", 64, &mut issues),
        source: text(obj, "source", 16, &mut issues),
        version: text(obj, "version", 32, &mut issues),
    };
    if manifest.description.is_empty() {
        issues.push(Issue::warning("description", "description_missing"));
    }
    let failed = issues.iter().any(|i| i.severity == Severity::Error);
    Report {
        manifest: (!failed).then_some(manifest),
        issues,
    }
}

#[must_use]
pub fn validate(raw: &str, folder: &str, folder_category: Option<&str>) -> Report {
    if raw.len() > MAX_MANIFEST_BYTES {
        return Report {
            manifest: None,
            issues: vec![Issue::error("", "too_large")],
        };
    }
    match serde_json::from_str::<Value>(raw) {
        Ok(value) => validate_value(&value, folder, folder_category),
        Err(_) => Report {
            manifest: None,
            issues: vec![Issue::error("", "invalid_json")],
        },
    }
}
