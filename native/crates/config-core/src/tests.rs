use crate::{
    ConfigError, apply_plan, is_secret, normalize_ollama, ollama_remote, ollama_url, parse_env,
    reload_units, rewrite_env, valid_key,
};

fn owned(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| (*s).to_owned()).collect()
}

fn pairs(items: &[(&str, &str)]) -> Vec<(String, String)> {
    items
        .iter()
        .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
        .collect()
}

#[test]
fn keys_and_secrets() {
    assert!(valid_key("NUXIVA_X1"));
    assert!(!valid_key("nuxiva"));
    assert!(!valid_key("_X"));
    assert!(!valid_key(""));
    assert!(is_secret("GEMINI_API_KEY", &[]));
    assert!(is_secret("MY_TOKEN_FILE", &[]));
    assert!(is_secret("CREDENTIALS", &[]));
    assert!(is_secret("MONKEY_X", &[]));
    assert!(!is_secret("NUXIVA_KEYBOARD", &[]));
    assert!(is_secret("CUSTOM", &["CUSTOM"]));
}

#[test]
fn parse_first_wins_and_decodes() {
    let parsed = parse_env("# c\nA=1\nA=2\n b = \"x y\" \nlower=1\n'Q'='z'\nnoeq");
    assert_eq!(parsed, pairs(&[("A", "1"), ("Q", "z")]));
}

#[test]
fn rewrite_updates_removes_and_appends() -> Result<(), ConfigError> {
    let text = "# top\nA=1\n\nB=\"old\"\nA=dup\nbad-key=1\nC=keep\n";
    let out = rewrite_env(text, &pairs(&[("B", "new"), ("C", ""), ("D", "'q'")]))?;
    assert_eq!(out, "# top\nA=\"1\"\nB=\"new\"\nD=\"q\"\n");
    assert_eq!(rewrite_env("", &[])?, "\n");
    assert!(matches!(
        rewrite_env("", &pairs(&[("a", "1")])),
        Err(ConfigError::Key(_))
    ));
    assert!(matches!(
        rewrite_env("", &pairs(&[("A", "1\r2")])),
        Err(ConfigError::Value(_))
    ));
    Ok(())
}

#[test]
fn ollama_addresses() {
    assert_eq!(
        ollama_url("", "http://127.0.0.1:11434"),
        "http://127.0.0.1:11434"
    );
    assert_eq!(
        ollama_url(" 192.168.1.50/ ", "d"),
        "http://192.168.1.50:11434"
    );
    assert_eq!(ollama_url("https://x:99", "d"), "https://x:99");
    assert_eq!(normalize_ollama("x").as_deref(), Some("http://x:11434"));
    assert_eq!(normalize_ollama("").as_deref(), Some(""));
    assert_eq!(normalize_ollama("http://a b"), None);
    assert_eq!(normalize_ollama("http://a//b"), None);
    assert!(ollama_remote("http://192.168.1.50:11434"));
    assert!(!ollama_remote("http://localhost:11434"));
}

#[test]
fn plans() {
    let known = owned(&["voice", "ear", "music", "services", "kiosk"]);
    assert_eq!(
        apply_plan(&owned(&["NUXIVA_EAR"]), &owned(&["kiosk"]), &known),
        owned(&["kiosk", "ear", "music"])
    );
    assert_eq!(
        apply_plan(&owned(&["UNKNOWN"]), &[], &known),
        [] as [std::string::String; 0]
    );
    assert_eq!(
        reload_units(&owned(&["NUXIVA_WAKE_WORD"])),
        owned(&["nuxiva-ear"])
    );
    assert_eq!(
        reload_units(&owned(&["NUXIVA_X"])),
        [] as [std::string::String; 0]
    );
}
