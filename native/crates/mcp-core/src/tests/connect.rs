use std::collections::BTreeMap;

use crate::{
    Isolation, McpError, MemorySecrets, NetworkPolicy, PolicyConfig, Risk, ServerEntry, Settings,
    TransportSpec, connect_server,
};

fn http(url: &str, secret: Option<&str>, network: Option<NetworkPolicy>) -> ServerEntry {
    ServerEntry {
        id: "srv".into(),
        enabled: true,
        max_risk: Risk::Files,
        honor_read_only: false,
        transport: TransportSpec::Http {
            url: url.into(),
            secret: secret.map(Into::into),
            network,
        },
    }
}

#[tokio::test]
async fn forbidden_destinations_never_connect() {
    let secrets = MemorySecrets::default();
    let policy = PolicyConfig::default();
    let settings = Settings::default();
    for url in [
        "https://169.254.169.254/",
        "http://127.0.0.1:1/",
        "https://10.1.1.1/",
    ] {
        let outcome = connect_server(&http(url, None, None), &secrets, &policy, &settings).await;
        assert_eq!(outcome.err(), Some(McpError::NetworkDenied), "{url}");
    }
}

#[tokio::test]
async fn disabled_and_secretless_entries_are_refused() {
    let secrets = MemorySecrets::default();
    let policy = PolicyConfig::default();
    let settings = Settings::default();
    let mut disabled = http("https://8.8.8.8/", None, None);
    disabled.enabled = false;
    assert_eq!(
        connect_server(&disabled, &secrets, &policy, &settings)
            .await
            .err(),
        Some(McpError::NotPermitted)
    );
    let lan = NetworkPolicy {
        allow_loopback: true,
        ..NetworkPolicy::default()
    };
    let missing = http("http://127.0.0.1:1/", Some("absent"), Some(lan));
    assert_eq!(
        connect_server(&missing, &secrets, &policy, &settings)
            .await
            .err(),
        Some(McpError::SecretMissing)
    );
}

#[tokio::test]
async fn stdio_secrets_are_resolved_and_validated() {
    let mut secrets = MemorySecrets::default();
    secrets.insert("tok", "value");
    let entry = ServerEntry {
        transport: TransportSpec::Stdio {
            program: "/nonexistent/server".into(),
            args: Vec::new(),
            env: BTreeMap::new(),
            secret_env: BTreeMap::from([("API_KEY".to_owned(), "tok".to_owned())]),
            isolation: Isolation::Sandboxed,
        },
        ..http("https://8.8.8.8/", None, None)
    };
    let outcome = connect_server(
        &entry,
        &secrets,
        &PolicyConfig::default(),
        &Settings::default(),
    )
    .await;
    assert_eq!(outcome.err(), Some(McpError::Io));
    let absent = ServerEntry {
        transport: TransportSpec::Stdio {
            program: "/bin/true".into(),
            args: Vec::new(),
            env: BTreeMap::new(),
            secret_env: BTreeMap::from([("API_KEY".to_owned(), "missing".to_owned())]),
            isolation: Isolation::Sandboxed,
        },
        ..entry
    };
    let outcome = connect_server(
        &absent,
        &secrets,
        &PolicyConfig::default(),
        &Settings::default(),
    )
    .await;
    assert_eq!(outcome.err(), Some(McpError::SecretMissing));
}

#[test]
fn secrets_never_appear_in_debug_output() {
    let mut secrets = MemorySecrets::default();
    secrets.insert("tok", "super-secret-value");
    let rendered = format!(
        "{secrets:?} {:?}",
        crate::SecretProvider::get(&secrets, "tok")
    );
    assert!(!rendered.contains("super-secret-value"));
}
