pub const DEFAULT_OLLAMA_PORT: &str = "11434";

fn strip_slashes(value: &str) -> &str {
    nuxiva_guard_core::py_strip(value).trim_end_matches('/')
}

fn with_scheme(url: &str) -> String {
    if url.starts_with("http://") || url.starts_with("https://") {
        url.to_owned()
    } else {
        format!("http://{url}")
    }
}

fn after_scheme(url: &str) -> &str {
    url.split_once("//").map_or("", |(_, rest)| rest)
}

fn ends_with_port(text: &str) -> bool {
    text.rsplit_once(':')
        .is_some_and(|(_, port)| !port.is_empty() && port.chars().all(|c| c.is_ascii_digit()))
}

#[must_use]
pub fn ollama_url(custom: &str, default: &str) -> String {
    let trimmed = strip_slashes(custom);
    if trimmed.is_empty() {
        return default.to_owned();
    }
    let mut url = with_scheme(trimmed);
    if !ends_with_port(after_scheme(&url)) {
        url.push(':');
        url.push_str(DEFAULT_OLLAMA_PORT);
    }
    url
}

pub fn normalize_ollama(value: &str) -> Option<String> {
    let trimmed = strip_slashes(value);
    if trimmed.is_empty() {
        return Some(String::new());
    }
    let mut url = with_scheme(trimmed);
    if !after_scheme(&url).contains(':') {
        url.push(':');
        url.push_str(DEFAULT_OLLAMA_PORT);
    }
    if url.chars().any(char::is_whitespace) || url.matches("//").count() != 1 {
        return None;
    }
    Some(url)
}

#[must_use]
pub fn ollama_remote(url: &str) -> bool {
    let rest = url.split_once("//").map_or(url, |(_, r)| r);
    let host = rest.split_once(':').map_or(rest, |(h, _)| h);
    !matches!(host, "127.0.0.1" | "localhost" | "::1" | "")
}
