mod cargo;
mod manifest;
mod markdown;
mod python;
mod rust;
mod script;
mod util;

use crate::model::{Facts, Language};
use crate::path::file_name;
use crate::settings::GraphSettings;

#[must_use]
pub fn language(path: &str) -> Language {
    let name = file_name(path);
    if name == "Cargo.toml" {
        return Language::Cargo;
    }
    if name == "feature.json" {
        return Language::Manifest;
    }
    match name.rsplit_once('.').map(|(_, ext)| ext) {
        Some("rs") => Language::Rust,
        Some("py") => Language::Python,
        Some("js" | "mjs" | "cjs" | "jsx" | "ts" | "tsx" | "mts" | "cts") => Language::Script,
        Some("md" | "markdown") => Language::Markdown,
        _ => Language::Other,
    }
}

#[must_use]
pub fn extract(language: Language, text: &str, settings: &GraphSettings) -> Facts {
    match language {
        Language::Rust => rust::extract(text, settings),
        Language::Python => python::extract(text, settings),
        Language::Script => script::extract(text, settings),
        Language::Cargo => cargo::extract(text, settings),
        Language::Manifest => manifest::extract(text, settings),
        Language::Markdown => markdown::extract(text, settings),
        Language::Other => Facts::default(),
    }
}
