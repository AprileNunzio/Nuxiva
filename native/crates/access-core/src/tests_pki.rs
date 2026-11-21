use crate::pki::{
    EnterprisePkiConfig, InterfaceSnapshot, KeyAlgorithm, NetworkCategory, build_pki_plan,
    classify_network_address, sanitize_dns_name,
};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};

#[test]
fn test_classify_tailscale_cgnat_v4() {
    let ts_ip = IpAddr::V4(Ipv4Addr::new(100, 115, 92, 44));
    assert_eq!(classify_network_address(&ts_ip), NetworkCategory::Tailscale);
}

#[test]
fn test_classify_local_lan_v4() {
    let lan1 = IpAddr::V4(Ipv4Addr::new(192, 168, 1, 150));
    let lan2 = IpAddr::V4(Ipv4Addr::new(10, 0, 4, 1));
    let lan3 = IpAddr::V4(Ipv4Addr::new(172, 20, 0, 5));
    assert_eq!(classify_network_address(&lan1), NetworkCategory::LocalLan);
    assert_eq!(classify_network_address(&lan2), NetworkCategory::LocalLan);
    assert_eq!(classify_network_address(&lan3), NetworkCategory::LocalLan);
}

#[test]
fn test_classify_loopback_v4_and_v6() {
    let v4 = IpAddr::V4(Ipv4Addr::LOCALHOST);
    let v6 = IpAddr::V6(Ipv6Addr::LOCALHOST);
    assert_eq!(classify_network_address(&v4), NetworkCategory::Loopback);
    assert_eq!(classify_network_address(&v6), NetworkCategory::Loopback);
}

#[test]
fn test_classify_public_v4() {
    let pub_ip = IpAddr::V4(Ipv4Addr::new(93, 184, 216, 34));
    assert_eq!(
        classify_network_address(&pub_ip),
        NetworkCategory::PublicDomain
    );
}

#[test]
fn test_sanitize_dns_name() {
    assert_eq!(
        sanitize_dns_name("Nuxiva.Local."),
        Some("nuxiva.local".to_string())
    );
    assert_eq!(
        sanitize_dns_name("my-node.ts.net"),
        Some("my-node.ts.net".to_string())
    );
    assert_eq!(sanitize_dns_name(""), None);
    assert_eq!(sanitize_dns_name("-bad-host"), None);
    assert_eq!(sanitize_dns_name("bad_char!"), None);
}

#[test]
fn test_build_pki_plan_incorporates_tailscale_and_vpn() {
    let cfg = EnterprisePkiConfig {
        organization: "Test Org".to_string(),
        common_name: "Test Root CA".to_string(),
        validity_days: 365,
        algorithm: KeyAlgorithm::EcdsaP256,
        enable_tailscale: true,
        enable_vpn: true,
        enable_lan: true,
        custom_dns: vec![
            "custom.nuxiva.internal".to_string(),
            "invalid..name".to_string(),
        ],
        custom_ips: vec!["192.168.1.200".to_string()],
    };

    let ifaces = vec![
        InterfaceSnapshot {
            name: "tailscale0".to_string(),
            addresses: vec!["100.64.1.2".to_string()],
            is_tailscale: true,
            is_vpn: false,
        },
        InterfaceSnapshot {
            name: "wg0".to_string(),
            addresses: vec!["10.8.0.1".to_string()],
            is_tailscale: false,
            is_vpn: true,
        },
        InterfaceSnapshot {
            name: "eth0".to_string(),
            addresses: vec!["192.168.1.50".to_string()],
            is_tailscale: false,
            is_vpn: false,
        },
    ];

    let extra_names = vec!["node.tailscale.ts.net".to_string()];
    let plan = build_pki_plan(&cfg, &ifaces, &extra_names);

    assert!(plan.has_tailscale);
    assert!(plan.has_vpn);
    assert_eq!(plan.algorithm, KeyAlgorithm::EcdsaP256);
    assert_eq!(plan.validity_days, 365);

    assert!(
        plan.sans
            .iter()
            .any(|s| s.value == "100.64.1.2" && s.category == NetworkCategory::Tailscale)
    );
    assert!(
        plan.sans
            .iter()
            .any(|s| s.value == "10.8.0.1" && s.category == NetworkCategory::WireguardVpn)
    );
    assert!(
        plan.sans
            .iter()
            .any(|s| s.value == "192.168.1.50" && s.category == NetworkCategory::LocalLan)
    );
    assert!(plan.sans.iter().any(|s| s.value == "node.tailscale.ts.net" && s.category == NetworkCategory::Tailscale));
    assert!(
        plan.sans
            .iter()
            .any(|s| s.value == "custom.nuxiva.internal")
    );
    assert_eq!(plan.warning_messages.len(), 1);
}

#[test]
fn test_build_pki_plan_disabled_tailscale_skips_interface() {
    let cfg = EnterprisePkiConfig {
        enable_tailscale: false,
        ..Default::default()
    };

    let ifaces = vec![InterfaceSnapshot {
        name: "tailscale0".to_string(),
        addresses: vec!["100.64.1.2".to_string()],
        is_tailscale: true,
        is_vpn: false,
    }];

    let plan = build_pki_plan(&cfg, &ifaces, &[]);
    assert!(!plan.sans.iter().any(|s| s.value == "100.64.1.2"));
    assert!(!plan.has_tailscale);
}
