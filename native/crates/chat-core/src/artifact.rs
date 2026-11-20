use crate::types::Artifact;
use regex::Regex;

#[derive(Debug, Clone)]
pub struct ArtifactParser {
    fenced_re: Regex,
}

impl Default for ArtifactParser {
    fn default() -> Self {
        Self::new()
    }
}

impl ArtifactParser {
    #[must_use]
    pub fn new() -> Self {
        let pattern = r"```([a-zA-Z0-9_-]+)?(?:\s+filename=([^\n]+))?\n([\s\S]*?)```";
        let fenced_re = match Regex::new(pattern) {
            Ok(re) => re,
            Err(_) => match Regex::new(r"```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```") {
                Ok(fallback) => fallback,
                Err(_) => {
                    unreachable!()
                }
            },
        };
        Self { fenced_re }
    }

    #[must_use]
    pub fn extract(&self, text: &str) -> Vec<Artifact> {
        let mut artifacts = Vec::new();
        let mut index: usize = 0;

        for caps in self.fenced_re.captures_iter(text) {
            let lang = caps.get(1).map(|m| m.as_str().to_lowercase());
            let raw_content = caps.get(3).or_else(|| caps.get(2));
            let content = match raw_content {
                Some(m) => m.as_str().trim().to_string(),
                None => continue,
            };

            if content.is_empty() {
                continue;
            }

            index = index.saturating_add(1);
            let explicit_name = caps.get(2).and_then(|m| {
                if caps.get(3).is_some() {
                    Some(m.as_str().trim().to_string())
                } else {
                    None
                }
            });

            let language_str = lang.as_deref().unwrap_or("text");
            let kind = match language_str {
                "html" | "svg" | "react" | "tsx" | "jsx" => "ui_component",
                "rust" | "python" | "javascript" | "ts" | "typescript" | "sh" | "bash" | "json" => {
                    "code"
                }
                "mermaid" => "diagram",
                "markdown" | "md" => "document",
                _ => "snippet",
            };

            let title =
                explicit_name.unwrap_or_else(|| format!("Artifact {index} ({language_str})"));
            let id = format!("art_{index}_{language_str}");

            artifacts.push(Artifact {
                id,
                title,
                kind: kind.to_string(),
                content,
                language: Some(language_str.to_string()),
            });
        }

        artifacts
    }
}
