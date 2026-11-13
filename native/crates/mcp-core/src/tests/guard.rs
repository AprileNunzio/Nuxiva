use std::net::IpAddr;

use crate::{IpClass, McpError, NetworkPolicy, admit, classify_ip, parse_target, resolve};

fn ip(text: &str) -> IpAddr {
    text.parse().unwrap_or(IpAddr::from([0, 0, 0, 0]))
}

#[test]
fn addresses_are_classified() {
    let cases = [
        ("8.8.8.8", IpClass::Public),
        ("10.1.2.3", IpClass::Private),
        ("172.20.0.1", IpClass::Private),
        ("192.168.1.9", IpClass::Private),
        ("100.64.0.1", IpClass::Private),
        ("127.0.0.1", IpClass::Loopback),
        ("169.254.169.254", IpClass::Metadata),
        ("169.254.1.1", IpClass::LinkLocal),
        ("0.0.0.0", IpClass::Reserved),
        ("224.0.0.1", IpClass::Reserved),
        ("203.0.113.5", IpClass::Reserved),
        ("::1", IpClass::Loopback),
        ("fe80::1", IpClass::LinkLocal),
        ("fd00:ec2::254", IpClass::Metadata),
        ("fc00::1", IpClass::Private),
        ("::ffff:169.254.169.254", IpClass::Metadata),
        ("::ffff:10.0.0.1", IpClass::Private),
        ("2606:4700::1", IpClass::Public),
    ];
    for (text, class) in cases {
        assert_eq!(classify_ip(ip(text)), class, "{text}");
    }
}

#[test]
fn admission_follows_policy() {
    let strict = NetworkPolicy::default();
    assert!(admit(ip("8.8.8.8"), &strict, true));
    assert!(!admit(ip("8.8.8.8"), &strict, false));
    assert!(!admit(ip("10.0.0.1"), &strict, true));
    assert!(!admit(ip("127.0.0.1"), &strict, true));
    let lan = NetworkPolicy {
        allow_private: true,
        allow_loopback: true,
        ports: Vec::new(),
    };
    assert!(admit(ip("10.0.0.1"), &lan, false));
    assert!(admit(ip("127.0.0.1"), &lan, false));
    assert!(!admit(ip("169.254.169.254"), &lan, true));
    assert!(!admit(ip("fd00:ec2::254"), &lan, false));
}

#[test]
fn urls_are_parsed_strictly() {
    for bad in [
        "ftp://x.test/",
        "file:///etc/passwd",
        "https://user:pw@x.test/",
        "https://x.test/#frag",
        "not a url",
    ] {
        assert_eq!(
            parse_target(bad).err(),
            Some(McpError::NetworkDenied),
            "{bad}"
        );
    }
    let ok = parse_target("https://example.test:8443/mcp");
    assert!(ok.is_ok_and(|t| t.port == 8443 && t.secure));
}

#[tokio::test]
async fn resolution_blocks_forbidden_destinations() -> Result<(), McpError> {
    let strict = NetworkPolicy::default();
    for url in [
        "https://169.254.169.254/latest",
        "https://127.0.0.1/",
        "http://127.0.0.1/",
        "https://10.0.0.5/",
        "https://[::1]/",
    ] {
        let target = parse_target(url)?;
        assert_eq!(
            resolve(&target, &strict).await.err(),
            Some(McpError::NetworkDenied),
            "{url}"
        );
    }
    let lan = NetworkPolicy {
        allow_loopback: true,
        ports: vec![8080],
        ..NetworkPolicy::default()
    };
    assert!(
        resolve(&parse_target("http://127.0.0.1:8080/")?, &lan)
            .await
            .is_ok()
    );
    assert_eq!(
        resolve(&parse_target("http://127.0.0.1:9090/")?, &lan)
            .await
            .err(),
        Some(McpError::NetworkDenied)
    );
    assert!(
        resolve(&parse_target("https://127.0.0.1:8080/")?, &lan)
            .await
            .is_ok()
    );
    Ok(())
}
