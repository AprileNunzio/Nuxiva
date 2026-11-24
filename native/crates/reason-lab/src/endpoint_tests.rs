use crate::{Backend, endpoint_url};

#[test]
fn groq_always_reaches_the_openai_compatible_root() {
    for base in [
        "https://api.groq.com/openai/v1",
        "https://api.groq.com/openai/v1/",
        "https://api.groq.com",
        "https://api.groq.com/v1",
        "https://api.groq.com/openai/v1/chat/completions",
        "https://API.groq.com/openai/v1/models",
    ] {
        assert_eq!(
            endpoint_url(Backend::OpenAiCompatible, base),
            if base.contains("API.") {
                "https://API.groq.com/openai/v1/chat/completions".to_owned()
            } else {
                "https://api.groq.com/openai/v1/chat/completions".to_owned()
            },
            "{base}"
        );
    }
}

#[test]
fn openai_compatible_bases_never_get_a_double_version() {
    let cases = [
        (
            "https://api.openai.com/v1",
            "https://api.openai.com/v1/chat/completions",
        ),
        (
            "https://api.openai.com",
            "https://api.openai.com/v1/chat/completions",
        ),
        (
            "http://127.0.0.1:1234",
            "http://127.0.0.1:1234/v1/chat/completions",
        ),
        (
            "http://[::1]:8000/v1/",
            "http://[::1]:8000/v1/chat/completions",
        ),
        (
            "https://api.fireworks.ai/inference/v1",
            "https://api.fireworks.ai/inference/v1/chat/completions",
        ),
        (
            "https://api.perplexity.ai",
            "https://api.perplexity.ai/chat/completions",
        ),
        (
            "https://generativelanguage.googleapis.com",
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        ),
    ];
    for (base, expected) in cases {
        assert_eq!(
            endpoint_url(Backend::OpenAiCompatible, base),
            expected,
            "{base}"
        );
    }
}

#[test]
fn ollama_bases_are_reduced_to_the_server_root() {
    for base in [
        "http://127.0.0.1:11434",
        "http://127.0.0.1:11434/",
        "http://127.0.0.1:11434/v1",
        "http://127.0.0.1:11434/api",
        "http://127.0.0.1:11434/api/chat",
    ] {
        assert_eq!(
            endpoint_url(Backend::Ollama, base),
            "http://127.0.0.1:11434/api/chat",
            "{base}"
        );
    }
}
