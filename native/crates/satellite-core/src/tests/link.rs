use crate::link::{EnrollFile, LinkError, node_id, normalize_server, pem_fingerprint};

const PIN: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

fn enroll(server: &str, token: &str, pin: &str, expires: u64) -> String {
    serde_json::json!({"server": server, "token": token, "pin": pin, "expires": expires})
        .to_string()
}

#[test]
fn enrollment_file_is_strictly_validated() {
    let token = "AbCdEfGhIjKlMnOpQrStUv_-12";
    assert!(
        EnrollFile::parse(&enroll("https://nuxiva.local:8443", token, PIN, 2000), 1000).is_ok()
    );
    assert_eq!(
        EnrollFile::parse(&enroll("https://nuxiva.local", token, PIN, 999), 1000).err(),
        Some("enroll_file_expired")
    );
    let bad = [
        enroll("http://nuxiva.local", token, PIN, 2000),
        enroll("https://user@evil", token, PIN, 2000),
        enroll("https://nuxiva.local/path", token, PIN, 2000),
        enroll("https://nuxiva.local", "short", PIN, 2000),
        enroll(
            "https://nuxiva.local",
            "token with spaces and more chars",
            PIN,
            2000,
        ),
        enroll("https://nuxiva.local", token, &PIN.to_uppercase(), 2000),
        enroll("https://nuxiva.local", token, "abc", 2000),
        "[]".to_owned(),
        "x".repeat(5000),
    ];
    for text in bad {
        assert_eq!(
            EnrollFile::parse(&text, 1000).err(),
            Some("enroll_file_invalid"),
            "{text}"
        );
    }
}

#[test]
fn server_addresses_are_normalised_and_https_only() {
    assert_eq!(
        normalize_server("https://Nuxiva.Local:8443/"),
        Ok("https://nuxiva.local:8443".to_owned())
    );
    assert_eq!(
        normalize_server("https://[fe80::1]:8443"),
        Ok("https://[fe80::1]:8443".to_owned())
    );
    for bad in [
        "http://a",
        "https://",
        "https://a/b",
        "https://a?b",
        "https://a#b",
        "ftp://a",
        "https://a b",
    ] {
        assert_eq!(
            normalize_server(bad),
            Err(LinkError::InvalidServer),
            "{bad}"
        );
    }
}

#[test]
fn node_ids_match_the_server_rules() {
    assert_eq!(node_id("Rock-5B", "Salotto Audio"), "rock-5b-salotto-audio");
    assert_eq!(node_id("a", "b"), "a-b");
    let long = node_id(&"x".repeat(80), "y");
    assert!(long.len() <= 40 && !long.ends_with('-'));
    assert!(node_id("", "").starts_with("nodo"));
}

#[test]
fn garbage_pem_has_no_fingerprint() {
    assert_eq!(
        pem_fingerprint("not a certificate"),
        Err(LinkError::Pin("ca_invalid"))
    );
}
