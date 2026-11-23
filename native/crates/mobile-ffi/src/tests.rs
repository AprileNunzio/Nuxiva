use crate::enroll::normalize_server;
use crate::identity::node_id_with;
use crate::{
    DeviceFacts, DeviceIdentity, ca_der, ca_fingerprint, heartbeat_body, normalize_code,
    normalize_server_input, parse_enrollment, pin_matches,
};
use serde_json::Value;
use sha2::{Digest, Sha256};

const CONTRACT: &str = include_str!("../../../../contracts/android_enrollment.json");
const PEM: &str = "-----BEGIN CERTIFICATE-----
MIIBiTCCAS+gAwIBAgIUPmSqx4ghitdC0VwQzeh+bit9l9swCgYIKoZIzj0EAwIw
GTEXMBUGA1UEAwwOTnV4aXZhIFRlc3QgQ0EwIBcNMjYxMTIzMDgyOTE5WhgPMjEy
NjEwMzAwODI5MTlaMBkxFzAVBgNVBAMMDk51eGl2YSBUZXN0IENBMFkwEwYHKoZI
zj0CAQYIKoZIzj0DAQcDQgAEmJkvGuE/blCammFZRa01s6zFiyVFFGoMXMMjNXA3
jSWMRvcf2rlngomCdWJKKfwl3vyviS08wQNCMFtceXGAeqNTMFEwHQYDVR0OBBYE
FIpg94L7WK/zK4NBxuvQ9XwS7Z3GMB8GA1UdIwQYMBaAFIpg94L7WK/zK4NBxuvQ
9XwS7Z3GMA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0EAwIDSAAwRQIhAOQo2R1w
GJlQAM72Pnx+h0zxXYcY+dkg67qNvNTM++iqAiBK1mG/d6EJsHYEm5o4gv4UQJIj
nHWoB1Z+rSTc0cgWMA==
-----END CERTIFICATE-----
";
const PEM_SHA256: &str = "0b7a27cf25a4d69099a057af63164a422560304bbbec8ecaab151b007202f4f5";

fn code(error: crate::MobileError) -> String {
    let crate::MobileError::Rejected { code } = error;
    code
}

#[test]
fn contract_links_decode_to_their_payloads() {
    let contract: Value = serde_json::from_str(CONTRACT).expect("contract");
    let now = contract["now"].as_i64().expect("now");
    for case in contract["cases"].as_array().expect("cases") {
        let parsed =
            parse_enrollment(case["link"].as_str().expect("link"), now).expect("valid link");
        let payload = &case["payload"];
        let server = normalize_server(payload["server"].as_str().expect("server")).expect("server");
        assert_eq!(parsed.server, server);
        assert_eq!(parsed.token, payload["token"].as_str().expect("token"));
        assert_eq!(parsed.pin, payload["pin"].as_str().expect("pin"));
        assert_eq!(
            parsed.expires,
            payload["expires"].as_i64().expect("expires")
        );
        assert_eq!(parsed.peer, "");
    }
}

#[test]
fn raw_json_and_base64_forms_are_accepted() {
    let body = r#"{"server":"https://nuxiva.local:443/","token":"Zk3-_Q9xZk3-_Q9xZk3-_Q9x","pin":"2a730b6bb9e9da2751672b97bc23c547121319d4f52ec0d93eeaea8d6f33c41e","expires":2000.7}"#;
    let parsed = parse_enrollment(body, 1000).expect("json");
    assert_eq!(
        (parsed.server.as_str(), parsed.expires),
        ("https://nuxiva.local", 2000)
    );
    let encoded = base64::Engine::encode(&base64::engine::general_purpose::URL_SAFE_NO_PAD, body);
    assert_eq!(
        parse_enrollment(&format!(" \"{encoded}\" "), 1000).expect("b64"),
        parsed
    );
}

#[test]
fn expired_insecure_and_malformed_payloads_are_rejected() {
    let base = r#"{"server":"SERVER","token":"Zk3-_Q9xZk3-_Q9xZk3-_Q9x","pin":"2a730b6bb9e9da2751672b97bc23c547121319d4f52ec0d93eeaea8d6f33c41e","expires":10}"#;
    let with = |server: &str| base.replace("SERVER", server);
    assert_eq!(
        code(parse_enrollment(&with("https://a.b"), 11).expect_err("expired")),
        "enroll_file_expired"
    );
    for server in [
        "http://a.b",
        "https://a..b",
        "https://-a.b",
        "https://a.b:0",
        "https://a.b:70000",
        "https://a b",
        "https://[zz]",
    ] {
        assert_eq!(
            code(parse_enrollment(&with(server), 1).expect_err(server)),
            "enroll_file_invalid"
        );
    }
    assert!(parse_enrollment("nuxiva://other?d=e30", 1).is_err());
    assert!(parse_enrollment("nuxiva://enroll?x=e30", 1).is_err());
    assert!(parse_enrollment("%%%", 1).is_err());
    assert!(parse_enrollment(&base.replace("Zk3-_Q9xZk3-_Q9xZk3-_Q9x", "short"), 1).is_err());
    assert!(parse_enrollment(&base.replace(r#""expires":10"#, r#""expires":"10""#), 1).is_err());
    assert!(parse_enrollment(&base.replace('}', r#","peer":"xyz"}"#), 1).is_err());
}

#[test]
fn codes_and_server_inputs_are_normalised() {
    assert_eq!(normalize_code("12 34-56").expect("code"), "123456");
    assert_eq!(
        code(normalize_code("12345").expect_err("short")),
        "enroll_code_invalid"
    );
    assert_eq!(
        normalize_server_input("nuxiva.local:8443/").expect("input"),
        "https://nuxiva.local:8443"
    );
    assert_eq!(
        normalize_server_input("https://[fe80::1]").expect("v6"),
        "https://[fe80::1]"
    );
    assert!(normalize_server_input("nu xiva").is_err());
}

#[test]
fn ca_fingerprint_matches_openssl() {
    assert_eq!(ca_fingerprint(PEM).expect("pem"), PEM_SHA256);
    let der = ca_der(PEM).expect("der");
    assert_eq!(hex(&Sha256::digest(&der)), PEM_SHA256);
    assert!(ca_fingerprint("nope").is_err());
    assert!(ca_fingerprint(&PEM.replace("MIIB", "MIIC")).is_err());
}

#[test]
fn pins_compare_case_insensitively_and_reject_mismatch() {
    assert!(pin_matches(&PEM_SHA256.to_uppercase(), PEM_SHA256));
    assert!(!pin_matches(PEM_SHA256, &PEM_SHA256.replace('0', "1")));
    assert!(!pin_matches("", ""));
}

#[test]
fn signatures_verify_with_the_server_rules() {
    let identity = DeviceIdentity::generate().expect("key");
    let restored = DeviceIdentity::from_seed_hex(identity.seed_hex()).expect("seed");
    assert_eq!(identity.public_hex(), restored.public_hex());
    let body = br#"{"a":1}"#.to_vec();
    let signed = restored
        .sign(
            "ios-iphone-abcdef".to_owned(),
            "POST",
            "/api/nodes/heartbeat",
            &body,
            1_760_000_000,
        )
        .expect("sign");
    nuxiva_node_core::identity::verify_request(
        &identity.public_hex(),
        &signed.signature,
        &signed.node,
        "POST",
        "/api/nodes/heartbeat",
        signed.ts,
        &signed.nonce,
        &hex(&Sha256::digest(&body)),
        1_760_000_000,
    )
    .expect("verified");
    assert!(DeviceIdentity::from_seed_hex("zz".to_owned()).is_err());
}

#[test]
fn node_ids_follow_the_server_pattern() {
    assert_eq!(
        node_id_with("iPhone 17 Pro", [0xab, 0x01, 0xff]),
        "ios-iphone-17-pro-ab01ff"
    );
    assert_eq!(node_id_with("???", [0, 0, 1]), "ios-device-000001");
    let long = node_id_with(&"x".repeat(80), [1, 2, 3]);
    assert!(long.len() <= 48);
}

#[test]
fn heartbeat_announces_display_and_optional_sensors() {
    let facts = DeviceFacts {
        version: "1.0.0".to_owned(),
        hostname: "iPad\u{0}".to_owned(),
        microphone: true,
        camera: false,
        cpu_cores: 6,
        ram_mb: 8192,
    };
    let body: Value = serde_json::from_str(&heartbeat_body(facts)).expect("json");
    assert_eq!(body["agent"], "ios");
    assert_eq!(body["hostname"], "iPad");
    let scopes: Vec<&str> = body["announce"]["capabilities"]
        .as_array()
        .expect("caps")
        .iter()
        .filter_map(|c| c["scope"].as_str())
        .collect();
    assert_eq!(
        scopes,
        [
            "audio.capture",
            "audio.play",
            "display.render",
            "telemetry.report"
        ]
    );
}

fn hex(bytes: &[u8]) -> String {
    nuxiva_node_core::hexutil::encode(bytes)
}
