use crate::origin::{is_host_origin, normalized_locals, parse_address};
use std::net::IpAddr;

fn locals() -> Vec<IpAddr> {
    normalized_locals(&[
        "192.168.1.197".to_owned(),
        "10.0.0.5".to_owned(),
        "fe80::1%eth0".to_owned(),
        "2001:db8::10".to_owned(),
        "172.17.0.2".to_owned(),
        "0.0.0.0".to_owned(),
        "garbage".to_owned(),
    ])
}

#[test]
fn loopback_peer_with_loopback_host_is_host() {
    let own = locals();
    assert!(is_host_origin("127.0.0.1", "localhost:8080", &own));
    assert!(is_host_origin("::1", "[::1]:8080", &own));
    assert!(is_host_origin("127.0.0.5", "127.0.0.1", &own));
    assert!(is_host_origin("localhost", "LOCALHOST.", &own));
}

#[test]
fn own_interface_address_is_host_on_every_family() {
    let own = locals();
    assert!(is_host_origin("192.168.1.197", "192.168.1.197", &own));
    assert!(is_host_origin("192.168.1.197", "192.168.1.197:80", &own));
    assert!(is_host_origin("10.0.0.5", "localhost", &own));
    assert!(is_host_origin("172.17.0.2", "172.17.0.2", &own));
    assert!(is_host_origin("2001:db8::10", "[2001:db8::10]:80", &own));
    assert!(is_host_origin("fe80::1%eth0", "[fe80::1]", &own));
    assert!(is_host_origin(
        "::ffff:192.168.1.197",
        "192.168.1.197",
        &own
    ));
}

#[test]
fn foreign_lan_clients_stay_remote() {
    let own = locals();
    assert!(!is_host_origin("192.168.1.20", "192.168.1.197", &own));
    assert!(!is_host_origin("192.168.1.20", "localhost", &own));
    assert!(!is_host_origin("2001:db8::99", "[2001:db8::10]", &own));
    assert!(!is_host_origin("8.8.8.8", "127.0.0.1", &own));
}

#[test]
fn names_that_could_rebind_are_never_host() {
    let own = locals();
    assert!(!is_host_origin("127.0.0.1", "nuxiva.local", &own));
    assert!(!is_host_origin("127.0.0.1", "evil.example:80", &own));
    assert!(!is_host_origin("192.168.1.197", "nuxiva.lan", &own));
    assert!(!is_host_origin("127.0.0.1", "localhost.evil.example", &own));
}

#[test]
fn foreign_or_malformed_host_addresses_are_rejected() {
    let own = locals();
    assert!(!is_host_origin("192.168.1.197", "192.168.1.20", &own));
    assert!(!is_host_origin("127.0.0.1", "", &own));
    assert!(!is_host_origin("127.0.0.1", "[::1", &own));
    assert!(!is_host_origin("127.0.0.1", "local\nhost", &own));
    assert!(!is_host_origin("", "localhost", &own));
    assert!(!is_host_origin("not-an-ip", "localhost", &own));
}

#[test]
fn unspecified_and_multicast_addresses_never_count() {
    let own = normalized_locals(&[
        "0.0.0.0".to_owned(),
        "224.0.0.1".to_owned(),
        "::".to_owned(),
    ]);
    assert!(own.is_empty());
    assert!(!is_host_origin("0.0.0.0", "0.0.0.0", &own));
    assert!(!is_host_origin("224.0.0.1", "224.0.0.1", &own));
    assert!(!is_host_origin("::", "[::]", &own));
}

#[test]
fn an_empty_local_set_still_trusts_only_loopback() {
    assert!(is_host_origin("127.0.0.1", "localhost", &[]));
    assert!(!is_host_origin("192.168.1.197", "192.168.1.197", &[]));
}

#[test]
fn address_parsing_unmaps_and_strips_scope() {
    assert_eq!(parse_address("::ffff:10.0.0.5"), "10.0.0.5".parse().ok());
    assert_eq!(parse_address("fe80::1%wlan0"), "fe80::1".parse().ok());
    assert_eq!(parse_address(&"1".repeat(300)), None);
}

#[test]
fn the_local_set_is_bounded() {
    let many: Vec<String> = (0u8..10)
        .flat_map(|a| (0u8..=249).map(move |b| format!("10.1.{a}.{b}")))
        .collect();
    assert_eq!(normalized_locals(&many).len(), 512);
}
