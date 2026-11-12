use crate::manifest::{self, Issue, Severity};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::Path;

pub const LANGUAGES: &[&str] = &["it", "en", "fr", "es"];
pub const PACKAGES: &[&str] = &["tools", "skills", "algorithms"];
pub const WIDGET_DIR: &str = "widget";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayoutReport {
    pub missing: Vec<String>,
    pub optional_missing: Vec<String>,
    pub complete: bool,
    pub score: u8,
}

fn real_file(path: &Path) -> bool {
    std::fs::symlink_metadata(path).is_ok_and(|m| m.file_type().is_file())
}

fn real_dir(path: &Path) -> bool {
    std::fs::symlink_metadata(path).is_ok_and(|m| m.file_type().is_dir())
}

fn package(dir: &Path, name: &str) -> bool {
    real_file(&dir.join(format!("{name}.py"))) || real_file(&dir.join(name).join("__init__.py"))
}

#[must_use]
pub fn required_parts() -> Vec<String> {
    let mut parts = vec![
        "feature.json".to_owned(),
        "agent.py".to_owned(),
        "icon.png".to_owned(),
    ];
    parts.extend(PACKAGES.iter().map(|p| format!("{p}/")));
    parts.extend(LANGUAGES.iter().map(|l| format!("language/{l}.json")));
    parts
}

#[must_use]
pub fn inspect(dir: &Path) -> LayoutReport {
    let mut missing = Vec::new();
    for file in ["feature.json", "agent.py", "icon.png"] {
        if !real_file(&dir.join(file)) {
            missing.push(file.to_owned());
        }
    }
    for name in PACKAGES {
        if !package(dir, name) {
            missing.push(format!("{name}/"));
        }
    }
    for lang in LANGUAGES {
        let rel = format!("language/{lang}.json");
        if !real_file(&dir.join(&rel)) {
            missing.push(rel);
        }
    }
    let optional_missing = if real_dir(&dir.join(WIDGET_DIR)) {
        Vec::new()
    } else {
        vec![format!("{WIDGET_DIR}/")]
    };
    let total = required_parts().len();
    let present = total.saturating_sub(missing.len());
    let score = present.saturating_mul(100).checked_div(total).unwrap_or(0);
    LayoutReport {
        complete: missing.is_empty(),
        score: u8::try_from(score).unwrap_or(100),
        missing,
        optional_missing,
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ScaffoldSpec {
    pub id: String,
    pub category: String,
    pub name: String,
    pub description: String,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub nouns: Vec<String>,
    #[serde(default)]
    pub phrases: Vec<String>,
    #[serde(default)]
    pub icon: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ScaffoldFile {
    pub path: String,
    pub bytes: Vec<u8>,
}

fn error(field: &str, code: &str) -> Issue {
    Issue {
        field: field.to_owned(),
        code: code.to_owned(),
        severity: Severity::Error,
    }
}

fn py_literal(text: &str) -> String {
    serde_json::to_string(text).unwrap_or_else(|_| "\"\"".to_owned())
}

fn manifest_value(spec: &ScaffoldSpec) -> Value {
    json!({
        "id": spec.id,
        "name": spec.name,
        "icon": if spec.icon.is_empty() { "◆" } else { spec.icon.as_str() },
        "category": spec.category,
        "version": "1.0.0",
        "description": spec.description,
        "capabilities": spec.capabilities,
        "routing": {"nouns": spec.nouns, "phrases": spec.phrases, "verbs": []},
        "profile": {"ram_mb": 64, "vram_mb": 0, "heavy": false},
        "tools": [format!("{}_describe", spec.id)],
        "skills": [],
        "widgets": [],
        "icon3d": "./icon.png"
    })
}

fn agent_py(spec: &ScaffoldSpec) -> String {
    format!(
        "from agenti._registry import registry\n\nAGENT_ID = {id}\n\n\nclass Agent:\n    agent_id = AGENT_ID\n\n    \
         def __init__(self) -> None:\n        self.running = False\n\n    @property\n    def manifest(self) -> dict:\n        \
         found = registry.get(AGENT_ID)\n        return dict(found.manifest) if found else {{}}\n\n    \
         def start(self) -> None:\n        self.running = True\n\n    def stop(self) -> None:\n        self.running = False\n\n    \
         def describe(self) -> dict:\n        m = self.manifest\n        \
         return {{\"id\": AGENT_ID, \"name\": m.get(\"name\", AGENT_ID), \"capabilities\": list(m.get(\"capabilities\", []))}}\n\n\n\
         agent = Agent()\n",
        id = py_literal(&spec.id)
    )
}

fn tools_py(spec: &ScaffoldSpec) -> String {
    format!(
        "from agenti.agent.registry import tool\nfrom agenti.{id}.agent import agent\n\n\n\
         @tool({name}, {desc}, {{}}, agent={idl})\nasync def {id}_describe() -> dict:\n    return agent.describe()\n",
        id = spec.id,
        idl = py_literal(&spec.id),
        name = py_literal(&format!("{}_describe", spec.id)),
        desc = py_literal(&spec.description),
    )
}

fn language(spec: &ScaffoldSpec, lang: &str) -> String {
    let value = json!({
        "meta": {"locale": lang},
        "name": spec.name,
        "description": spec.description,
        "capabilities": spec.capabilities,
        "scope": format!("features/{}", spec.id),
        "dictionary": {"name": spec.name, "description": spec.description},
    });
    serde_json::to_string_pretty(&value).unwrap_or_default()
}

pub fn scaffold(spec: &ScaffoldSpec) -> Result<Vec<ScaffoldFile>, Vec<Issue>> {
    let mut issues = Vec::new();
    if !manifest::known_category(&spec.category) {
        issues.push(error("category", "category_unknown"));
    }
    let value = manifest_value(spec);
    let report = manifest::validate_value(&value, &spec.id, Some(&spec.category));
    issues.extend(
        report
            .issues
            .into_iter()
            .filter(|i| i.severity == Severity::Error),
    );
    if spec.description.trim().is_empty() {
        issues.push(error("description", "description_missing"));
    }
    if !issues.is_empty() {
        return Err(issues);
    }
    let text = |path: String, body: String| ScaffoldFile {
        path,
        bytes: body.into_bytes(),
    };
    let mut files = vec![
        text(
            "feature.json".into(),
            serde_json::to_string_pretty(&value).unwrap_or_default(),
        ),
        text("agent.py".into(), agent_py(spec)),
        text("__init__.py".into(), String::new()),
        text(
            "tools/__init__.py".into(),
            format!(
                "from agenti.{0}.tools import {0}_tools\n\n__all__ = [\"{0}_tools\"]\n",
                spec.id
            ),
        ),
        text(format!("tools/{}_tools.py", spec.id), tools_py(spec)),
        text("skills/__init__.py".into(), "SKILLS: tuple = ()\n".into()),
        text(
            "algorithms/__init__.py".into(),
            "ALGORITHMS: tuple = ()\n".into(),
        ),
    ];
    files.extend(
        LANGUAGES
            .iter()
            .map(|lang| text(format!("language/{lang}.json"), language(spec, lang))),
    );
    files.push(ScaffoldFile {
        path: "icon.png".into(),
        bytes: crate::icon::render(&spec.category, &spec.id),
    });
    Ok(files)
}
