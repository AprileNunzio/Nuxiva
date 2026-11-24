use crate::Backend;

const KNOWN_ROOTS: [(&str, &str); 3] = [
    ("api.groq.com", "/openai/v1"),
    ("api.perplexity.ai", ""),
    ("generativelanguage.googleapis.com", "/v1beta/openai"),
];
const OPENAI_TAILS: [&str; 4] = ["/chat/completions", "/completions", "/models", "/responses"];
const OLLAMA_TAILS: [&str; 6] = [
    "/v1/chat/completions",
    "/api/generate",
    "/api/chat",
    "/api/tags",
    "/api",
    "/v1",
];

fn split(base: &str) -> (&str, &str) {
    let start = base.find("://").map_or(0, |i| i.saturating_add(3));
    let rest = base.get(start..).unwrap_or_default();
    rest.find('/').map_or((base, ""), |slash| {
        base.split_at(start.saturating_add(slash))
    })
}

fn host(origin: &str) -> String {
    let authority = origin.rsplit("://").next().unwrap_or_default();
    let name = if authority.starts_with('[') {
        authority.split(']').next().unwrap_or_default()
    } else {
        authority.split(':').next().unwrap_or_default()
    };
    name.trim_start_matches('[').to_ascii_lowercase()
}

fn strip<'a>(mut path: &'a str, tails: &[&str]) -> &'a str {
    loop {
        path = path.trim_end_matches('/');
        let lower = path.to_ascii_lowercase();
        let Some(tail) = tails.iter().find(|t| lower.ends_with(*t)) else {
            return path;
        };
        path = path
            .get(..path.len().saturating_sub(tail.len()))
            .unwrap_or_default();
    }
}

#[must_use]
pub fn url(backend: Backend, base: &str) -> String {
    let (origin, path) = split(base.trim().trim_end_matches('/'));
    let path = match backend {
        Backend::Ollama => strip(path, &OLLAMA_TAILS).to_owned(),
        Backend::OpenAiCompatible => {
            let path = strip(path, &OPENAI_TAILS);
            let name = host(origin);
            KNOWN_ROOTS
                .iter()
                .find(|(known, _)| *known == name)
                .map_or_else(
                    || {
                        if path.is_empty() {
                            "/v1".to_owned()
                        } else {
                            path.to_owned()
                        }
                    },
                    |(_, root)| (*root).to_owned(),
                )
        }
    };
    format!("{origin}{path}/{}", backend.path())
}
