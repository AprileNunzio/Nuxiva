use crate::announce::{self, Hardware};
use crate::audit::{self, GENESIS};
use crate::authorize::{Verdict, authorize, effective};
use crate::profile::{Ceiling, Mode, Profile, resolve};
use crate::scope;

fn strings(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| (*s).to_owned()).collect()
}

const BIG: Hardware = Hardware {
    cpu_cores: 8,
    ram_mb: 16384,
};
const SMALL: Hardware = Hardware {
    cpu_cores: 2,
    ram_mb: 2048,
};
const OPEN: Ceiling = Ceiling {
    second_server: true,
};
const CLOSED: Ceiling = Ceiling {
    second_server: false,
};

#[test]
fn scope_validation() {
    assert!(scope::valid("audio.capture"));
    assert!(scope::valid("fs.read.home"));
    assert!(!scope::valid("audio"));
    assert!(!scope::valid("Audio.capture"));
    assert!(!scope::valid("a..b"));
    assert!(!scope::valid("a.b.c.d"));
    assert!(!scope::valid(""));
    assert!(!scope::valid("audio.capture\n"));
    assert!(!scope::valid(&"a".repeat(60)));
}

#[test]
fn closed_ceiling_always_satellite() {
    for profile in [Profile::Satellite, Profile::SecondServer, Profile::Auto] {
        assert_eq!(resolve(profile, &BIG, true, CLOSED), Mode::Satellite);
    }
}

#[test]
fn open_ceiling_follows_profile() {
    assert_eq!(
        resolve(Profile::Satellite, &BIG, true, OPEN),
        Mode::Satellite
    );
    assert_eq!(
        resolve(Profile::SecondServer, &SMALL, false, OPEN),
        Mode::SecondServer
    );
    assert_eq!(resolve(Profile::Auto, &BIG, true, OPEN), Mode::SecondServer);
    assert_eq!(resolve(Profile::Auto, &SMALL, true, OPEN), Mode::Satellite);
    assert_eq!(resolve(Profile::Auto, &BIG, false, OPEN), Mode::Satellite);
}

#[test]
fn unknown_profile_is_satellite() {
    assert_eq!(Profile::parse("root"), Profile::Satellite);
    assert_eq!(Profile::parse("second_server"), Profile::SecondServer);
    assert_eq!(Profile::parse("auto"), Profile::Auto);
}

#[test]
fn satellite_never_gets_server_scopes() {
    let announced = strings(&["audio.capture", "compute.lease", "fs.write", "mcp.serve"]);
    let got = effective(Mode::Satellite, &announced, &strings(&["fs.write"]));
    assert_eq!(got, strings(&["audio.capture"]));
}

#[test]
fn second_server_grants_extra_but_elevated_needs_grant() {
    let announced = strings(&[
        "audio.capture",
        "compute.lease",
        "fs.write",
        "process.exec",
        "mcp.serve",
    ]);
    let got = effective(Mode::SecondServer, &announced, &strings(&["fs.write"]));
    assert_eq!(
        got,
        strings(&["audio.capture", "compute.lease", "fs.write", "mcp.serve"])
    );
}

#[test]
fn unannounced_is_never_effective() {
    let got = effective(
        Mode::SecondServer,
        &strings(&["audio.capture"]),
        &strings(&["fs.write", "compute.lease"]),
    );
    assert_eq!(got, strings(&["audio.capture"]));
}

#[test]
fn forbidden_domains_never_effective() {
    let got = effective(
        Mode::SecondServer,
        &strings(&["admin.users", "vault.read", "identity.rotate"]),
        &strings(&["admin.users"]),
    );
    assert!(got.is_empty());
}

#[test]
fn authorize_codes() {
    let eff = strings(&["audio.capture"]);
    assert_eq!(authorize(&eff, "audio.capture"), Verdict::Allow);
    assert_eq!(
        authorize(&eff, "compute.lease"),
        Verdict::Deny("node.error.scope_not_granted")
    );
    assert_eq!(
        authorize(&eff, "admin.users"),
        Verdict::Deny("node.error.scope_forbidden")
    );
    assert_eq!(
        authorize(&eff, "BAD"),
        Verdict::Deny("node.error.scope_invalid")
    );
}

#[test]
fn announce_filters_and_bounds() {
    let json = r#"{"capabilities":[{"scope":"audio.capture"},{"scope":"audio.capture"},{"scope":"admin.users"},{"scope":"BAD"},{"scope":"node.host_full"}],"hardware":{"cpu_cores":8,"ram_mb":16384}}"#;
    let parsed = announce::parse(json).expect("valid");
    assert_eq!(parsed.scopes, strings(&["audio.capture", "node.host_full"]));
    assert_eq!(parsed.rejected, strings(&["BAD", "admin.users"]));
    assert!(parsed.full_host);
    assert_eq!(parsed.hardware, BIG);
}

#[test]
fn announce_rejects_garbage() {
    assert!(announce::parse("not json").is_err());
    assert!(announce::parse(&" ".repeat(announce::MAX_ANNOUNCE + 1)).is_err());
    let many: Vec<String> = (0..65)
        .map(|i| format!("{{\"scope\":\"a.b{i}\"}}"))
        .collect();
    assert!(announce::parse(&format!("{{\"capabilities\":[{}]}}", many.join(","))).is_err());
}

#[test]
fn announce_clamps_hardware() {
    let parsed =
        announce::parse(r#"{"hardware":{"cpu_cores":99999999,"ram_mb":18446744073709551615}}"#)
            .expect("valid");
    assert_eq!(parsed.hardware.cpu_cores, 4096);
    assert_eq!(parsed.hardware.ram_mb, 16 * 1024 * 1024);
}

#[test]
fn audit_chain_detects_tampering() {
    let first = audit::seal(GENESIS, 1, 100, "admin", "pc-1", "pair.approve", "ok");
    let second = audit::seal(
        &first.hash,
        2,
        101,
        "admin",
        "pc-1",
        "profile.set",
        "second_server",
    );
    let third = audit::seal(
        &second.hash,
        3,
        102,
        "node",
        "pc-1",
        "scope.deny",
        "fs.write",
    );
    let mut chain = vec![first, second, third];
    assert_eq!(audit::verify_chain(GENESIS, &chain), None);
    chain[1].detail = "satellite".into();
    assert_eq!(audit::verify_chain(GENESIS, &chain), Some(1));
    chain[1].detail = "second_server".into();
    chain.remove(0);
    assert_eq!(audit::verify_chain(GENESIS, &chain), Some(0));
}

#[test]
fn audit_strips_controls_and_limits() {
    let entry = audit::seal(GENESIS, 1, 0, "a\nb", "n", "x", &"d".repeat(900));
    assert_eq!(entry.actor, "ab");
    assert_eq!(entry.detail.len(), 512);
}
