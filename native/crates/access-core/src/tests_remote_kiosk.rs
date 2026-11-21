use crate::remote_kiosk::{
    ClientContext, KioskAdvisory, KioskScheme, MediaCapabilities, RemoteKioskConfig, evaluate_remote_kiosk,
};

#[test]
fn test_default_config_is_disabled() {
    let cfg = RemoteKioskConfig::default();
    assert!(!cfg.enabled);
    assert!(cfg.allow_http);
    assert!(cfg.require_private_network);
}

#[test]
fn test_denied_when_disabled() {
    let cfg = RemoteKioskConfig::default();
    let ctx = ClientContext {
        peer: "192.168.1.50",
        scheme: "http",
        host: "192.168.1.100",
        is_admin: false,
    };
    let verdict = evaluate_remote_kiosk(&cfg, &ctx);
    assert!(!verdict.allowed);
    assert_eq!(verdict.reason, "remote_kiosk.disabled");
    assert_eq!(verdict.media, MediaCapabilities::none());
}

#[test]
fn test_allowed_http_when_enabled() {
    let cfg = RemoteKioskConfig {
        enabled: true,
        ..Default::default()
    };
    let ctx = ClientContext {
        peer: "192.168.1.50",
        scheme: "http",
        host: "192.168.1.100",
        is_admin: false,
    };
    let verdict = evaluate_remote_kiosk(&cfg, &ctx);
    assert!(verdict.allowed);
    assert_eq!(verdict.reason, "remote_kiosk.authorized");
    assert!(verdict.media.camera_preview);
    assert!(verdict.media.microphone);
    assert!(!verdict.media.camera_probe);
}

#[test]
fn test_allowed_https_with_admin_probe() {
    let cfg = RemoteKioskConfig {
        enabled: true,
        ..Default::default()
    };
    let ctx = ClientContext {
        peer: "10.0.0.5",
        scheme: "https",
        host: "nuxiva.local",
        is_admin: true,
    };
    let verdict = evaluate_remote_kiosk(&cfg, &ctx);
    assert!(verdict.allowed);
    assert!(verdict.media.camera_preview);
    assert!(verdict.media.microphone);
    assert!(verdict.media.camera_probe);
}

#[test]
fn test_denied_public_ip_zero_trust() {
    let cfg = RemoteKioskConfig {
        enabled: true,
        ..Default::default()
    };
    let ctx = ClientContext {
        peer: "8.8.8.8",
        scheme: "http",
        host: "192.168.1.100",
        is_admin: false,
    };
    let verdict = evaluate_remote_kiosk(&cfg, &ctx);
    assert!(!verdict.allowed);
    assert_eq!(verdict.reason, "remote_kiosk.network.not_private");
    assert_eq!(verdict.media, MediaCapabilities::none());
}

#[test]
fn test_invalid_host_denied() {
    let cfg = RemoteKioskConfig {
        enabled: true,
        ..Default::default()
    };
    let ctx = ClientContext {
        peer: "192.168.1.50",
        scheme: "http",
        host: "bad@host/injection",
        is_admin: false,
    };
    let verdict = evaluate_remote_kiosk(&cfg, &ctx);
    assert!(!verdict.allowed);
    assert_eq!(verdict.reason, "remote_kiosk.host.invalid");
}

#[test]
fn test_advisory_lifecycle() {
    let mut adv = KioskAdvisory::new("5.8.14");
    assert!(adv.should_prompt("5.8.14"));

    adv.acknowledge(false, "5.8.14");
    assert!(!adv.should_prompt("5.8.14"));
    assert!(!adv.remote_enabled);

    assert!(adv.should_prompt("5.8.15"));

    adv.acknowledge(true, "5.8.15");
    assert!(!adv.should_prompt("5.8.15"));
    assert!(adv.remote_enabled);
}

#[test]
fn test_scheme_parsing() {
    assert_eq!(KioskScheme::parse("http"), Some(KioskScheme::Http));
    assert_eq!(KioskScheme::parse("HTTP"), Some(KioskScheme::Http));
    assert_eq!(KioskScheme::parse("https"), Some(KioskScheme::Https));
    assert_eq!(KioskScheme::parse("ftp"), None);
}
