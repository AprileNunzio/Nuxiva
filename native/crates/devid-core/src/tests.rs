use crate::{Known, Resolution, Seen, normalize_mac, randomized, resolve};

fn known(key: &str, mac: Option<&str>, ip: Option<&str>, hostname: Option<&str>) -> Known {
    Known {
        key: key.into(),
        mac: mac.map(Into::into),
        ip: ip.map(Into::into),
        hostname: hostname.map(Into::into),
    }
}

fn seen(mac: Option<&str>, ip: Option<&str>, hostname: Option<&str>) -> Seen {
    Seen {
        mac: mac.map(Into::into),
        ip: ip.map(Into::into),
        hostname: hostname.map(Into::into),
        own: false,
    }
}

fn res(key: &str, mac: Option<&str>, random: bool, merge: &[&str]) -> Resolution {
    Resolution {
        key: key.into(),
        mac: mac.map(Into::into),
        randomized: random,
        merge: merge.iter().map(|m| (*m).to_string()).collect(),
    }
}

#[test]
fn mac_is_normalized_and_rejects_garbage() {
    assert_eq!(
        normalize_mac("AA-BB-CC-DD-EE-FF").as_deref(),
        Some("aa:bb:cc:dd:ee:ff")
    );
    assert_eq!(
        normalize_mac("a0b1.c2d3.e4f5").as_deref(),
        Some("a0:b1:c2:d3:e4:f5")
    );
    assert_eq!(normalize_mac("ff:ff:ff:ff:ff:ff"), None);
    assert_eq!(normalize_mac("01:00:5e:00:00:01"), None);
    assert_eq!(normalize_mac("zz:bb:cc:dd:ee:ff"), None);
    assert_eq!(normalize_mac("<script>"), None);
    assert!(randomized("da:a1:19:00:00:01"));
    assert!(!randomized("a0:b1:c2:d3:e4:f5"));
}

#[test]
fn same_mac_with_new_ip_keeps_identity_and_absorbs_ip_orphan() {
    let list = vec![
        known(
            "a0:b1:c2:d3:e4:f5",
            Some("a0:b1:c2:d3:e4:f5"),
            Some("192.168.1.10"),
            None,
        ),
        known("ip:192.168.1.50", None, Some("192.168.1.50"), None),
    ];
    assert_eq!(
        resolve(
            &list,
            &seen(Some("A0:B1:C2:D3:E4:F5"), Some("192.168.1.50"), None)
        ),
        Some(res(
            "a0:b1:c2:d3:e4:f5",
            Some("a0:b1:c2:d3:e4:f5"),
            false,
            &["ip:192.168.1.50"]
        ))
    );
}

#[test]
fn rotating_private_mac_is_matched_by_hostname() {
    let list = vec![known(
        "da:a1:19:00:00:01",
        Some("da:a1:19:00:00:01"),
        Some("192.168.1.20"),
        Some("iPhone-di-Nunzio.local"),
    )];
    assert_eq!(
        resolve(
            &list,
            &seen(
                Some("de:ad:19:00:00:02"),
                Some("192.168.1.31"),
                Some("iphone-di-nunzio")
            )
        ),
        Some(res(
            "da:a1:19:00:00:01",
            Some("de:ad:19:00:00:02"),
            true,
            &[]
        ))
    );
}

#[test]
fn stable_mac_never_steals_another_identity() {
    let list = vec![known(
        "da:a1:19:00:00:01",
        Some("da:a1:19:00:00:01"),
        None,
        Some("tv"),
    )];
    assert_eq!(
        resolve(
            &list,
            &seen(Some("a0:b1:c2:d3:e4:f5"), Some("192.168.1.9"), Some("tv"))
        ),
        Some(res(
            "a0:b1:c2:d3:e4:f5",
            Some("a0:b1:c2:d3:e4:f5"),
            false,
            &[]
        ))
    );
}

#[test]
fn without_mac_hostname_then_ip_then_new() {
    let list = vec![
        known(
            "a0:b1:c2:d3:e4:f5",
            Some("a0:b1:c2:d3:e4:f5"),
            Some("192.168.1.10"),
            None,
        ),
        known("ip:192.168.1.70", None, Some("192.168.1.70"), Some("nas")),
    ];
    assert_eq!(
        resolve(&list, &seen(None, Some("192.168.1.99"), Some("NAS.local"))),
        Some(res("ip:192.168.1.70", None, false, &[]))
    );
    assert_eq!(
        resolve(&list, &seen(None, Some("192.168.1.10"), None)),
        Some(res("a0:b1:c2:d3:e4:f5", None, false, &[]))
    );
    assert_eq!(
        resolve(&list, &seen(None, Some("192.168.1.11"), None)),
        Some(res("ip:192.168.1.11", None, false, &[]))
    );
    assert_eq!(resolve(&list, &seen(None, None, None)), None);
}

#[test]
fn own_host_is_always_self() {
    let list = vec![known("ip:192.168.1.2", None, Some("192.168.1.2"), None)];
    let mut own = seen(None, Some("192.168.1.2"), None);
    own.own = true;
    assert_eq!(
        resolve(&list, &own),
        Some(res("self", None, false, &["ip:192.168.1.2"]))
    );
}

#[test]
fn json_contract_is_stable() {
    let list: Result<Vec<Known>, _> =
        serde_json::from_str(r#"[{"key":"ip:10.0.0.5","ip":"10.0.0.5"}]"#);
    let one: Result<Seen, _> =
        serde_json::from_str(r#"{"mac":"10:20:30:40:50:60","ip":"10.0.0.5"}"#);
    let out = match (list, one) {
        (Ok(list), Ok(one)) => serde_json::to_string(&resolve(&list, &one)).ok(),
        _ => None,
    };
    assert_eq!(
        out.as_deref(),
        Some(
            r#"{"key":"10:20:30:40:50:60","mac":"10:20:30:40:50:60","randomized":false,"merge":["ip:10.0.0.5"]}"#
        )
    );
}
