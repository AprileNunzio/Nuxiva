use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::layout::{ScaffoldFile, ScaffoldSpec, scaffold};
use crate::manifest::Issue;
use crate::text::has_control;
use crate::widget::{CATEGORIES, LANGUAGES, MAX_ICON, MAX_ID, MODES, check_manifest};

pub const MIN_AUTO_FORGE_RECURRING_GAPS: u32 = 2;
pub const MASTERY_PROMOTION_THRESHOLD_BPS: u16 = 8_500;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StudyMethod {
    AstIntrospection,
    CounterfactualSimulation,
    ProtocolProbing,
    ExecutionTraceDistillation,
    AdversarialEdgeTesting,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MetaCurriculum {
    pub domain_id: String,
    pub capability_gap_key: String,
    pub study_methods: Vec<StudyMethod>,
    pub hypothesis_key: String,
    pub verification_invariant_key: String,
    pub target_mastery_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WidgetForgeSpec {
    pub widget_id: String,
    pub category: String,
    pub icon: String,
    pub mode: String,
    pub title_by_lang: BTreeMap<String, String>,
    pub say_keys_by_lang: BTreeMap<String, BTreeMap<String, String>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ForgedWidgetBundle {
    pub widget_id: String,
    pub manifest_json: String,
    pub files: Vec<ScaffoldFile>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AutonomousCapabilityPackage {
    pub curriculum: MetaCurriculum,
    pub agent_files: Vec<ScaffoldFile>,
    pub widget_bundle: ForgedWidgetBundle,
    pub required_tool_names: Vec<String>,
}

fn clean_token(raw: &str, max_len: usize) -> Result<String, Issue> {
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed.len() > max_len || has_control(trimmed) {
        return Err(Issue::error("token", "invalid_or_control_chars"));
    }
    Ok(trimmed.to_owned())
}

pub fn synthesize_meta_curriculum(
    domain_id: &str,
    capability_gap_key: &str,
    observed_failures: u32,
) -> Result<MetaCurriculum, Issue> {
    let clean_domain = clean_token(domain_id, MAX_ID)?;
    let clean_gap = clean_token(capability_gap_key, 160)?;

    let mut methods = vec![
        StudyMethod::AstIntrospection,
        StudyMethod::ProtocolProbing,
        StudyMethod::ExecutionTraceDistillation,
    ];
    if observed_failures >= MIN_AUTO_FORGE_RECURRING_GAPS {
        methods.push(StudyMethod::CounterfactualSimulation);
        methods.push(StudyMethod::AdversarialEdgeTesting);
    }

    Ok(MetaCurriculum {
        domain_id: clean_domain.clone(),
        capability_gap_key: clean_gap,
        study_methods: methods,
        hypothesis_key: format!("i18n.curriculum.hypothesis.{clean_domain}"),
        verification_invariant_key: format!("i18n.curriculum.invariant.{clean_domain}"),
        target_mastery_bps: MASTERY_PROMOTION_THRESHOLD_BPS,
    })
}

pub fn forge_widget_bundle(spec: &WidgetForgeSpec) -> Result<ForgedWidgetBundle, Vec<Issue>> {
    let id = spec.widget_id.trim();
    if id.len() < 2 || id.len() > MAX_ID {
        return Err(vec![Issue::error("widget_id", "invalid_length")]);
    }
    if !CATEGORIES.contains(&spec.category.as_str()) {
        return Err(vec![Issue::error("category", "invalid")]);
    }
    if !MODES.contains(&spec.mode.as_str()) {
        return Err(vec![Issue::error("mode", "invalid")]);
    }
    if spec.icon.is_empty() || spec.icon.len() > MAX_ICON {
        return Err(vec![Issue::error("icon", "invalid")]);
    }

    let manifest_val: Value = json!({
        "id": id,
        "category": spec.category,
        "chrome": false,
        "simple": {
            "mode": spec.mode,
            "icon": spec.icon,
        }
    });

    let issues = check_manifest(&manifest_val);
    if !issues.is_empty() {
        return Err(issues);
    }

    let mut files = Vec::new();
    let manifest_json =
        serde_json::to_string_pretty(&manifest_val).unwrap_or_else(|_| "{}".to_owned());
    files.push(ScaffoldFile {
        path: "widget/widget.json".to_owned(),
        bytes: format!("{manifest_json}\n").into_bytes(),
    });

    for lang in LANGUAGES {
        let Some(title) = spec.title_by_lang.get(*lang) else {
            return Err(vec![Issue::error("title_by_lang", "missing_locale")]);
        };
        if title.trim().is_empty() || has_control(title) {
            return Err(vec![Issue::error("title_by_lang", "invalid_title")]);
        }
        let mut dict = serde_json::Map::new();
        dict.insert(
            "simple_title".to_owned(),
            Value::String(title.trim().to_owned()),
        );

        if let Some(say_map) = spec.say_keys_by_lang.get(*lang) {
            for (k, v) in say_map {
                if !k.starts_with("say_") || v.trim().is_empty() || has_control(v) {
                    return Err(vec![Issue::error("say_keys", "invalid_say_entry")]);
                }
                dict.insert(k.clone(), Value::String(v.trim().to_owned()));
            }
        }

        let lang_doc = json!({
            "language": lang,
            "dictionary": Value::Object(dict),
        });
        let content = serde_json::to_string_pretty(&lang_doc).unwrap_or_else(|_| "{}".to_owned());
        files.push(ScaffoldFile {
            path: format!("widget/language/{lang}.json"),
            bytes: format!("{content}\n").into_bytes(),
        });
    }

    Ok(ForgedWidgetBundle {
        widget_id: id.to_owned(),
        manifest_json,
        files,
    })
}

pub fn evolve_full_capability(
    agent_spec: &ScaffoldSpec,
    widget_spec: &WidgetForgeSpec,
    capability_gap_key: &str,
    observed_failures: u32,
    required_tools: &[String],
) -> Result<AutonomousCapabilityPackage, Vec<Issue>> {
    let curriculum =
        synthesize_meta_curriculum(&agent_spec.id, capability_gap_key, observed_failures)
            .map_err(|e| vec![e])?;
    let agent_files = scaffold(agent_spec)?;
    let widget_bundle = forge_widget_bundle(widget_spec)?;

    let mut clean_tools = Vec::with_capacity(required_tools.len());
    for tool in required_tools {
        let t = clean_token(tool, 40).map_err(|e| vec![e])?;
        clean_tools.push(format!("x_{}", t.trim_start_matches("x_")));
    }

    Ok(AutonomousCapabilityPackage {
        curriculum,
        agent_files,
        widget_bundle,
        required_tool_names: clean_tools,
    })
}
