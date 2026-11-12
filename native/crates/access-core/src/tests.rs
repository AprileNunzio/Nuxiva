use crate::capability::Capability;
use crate::decide::{Request, Strength, Verdict, decide};
use crate::matrix::Matrix;
use crate::role::Role;

fn caps(list: &[&str]) -> Vec<Capability> {
    list.iter()
        .filter_map(|c| Capability::parse(c).ok())
        .collect()
}

fn verdict(list: &[&str], role: Role, strength: Strength) -> Verdict {
    let matrix = Matrix::builtin().ok();
    let capabilities = caps(list);
    let req = Request {
        capabilities: &capabilities,
        role,
        strength,
        local: None,
        own: false,
    };
    matrix.map_or(Verdict::Deny("matrix"), |m| decide(&req, &m))
}

#[test]
fn capabilities_are_validated() {
    assert!(Capability::parse("home.light.set").is_ok());
    assert!(Capability::parse("risk.home").is_ok());
    for bad in [
        "",
        "home",
        "home..set",
        "Home.light.set",
        "a.b.c.d",
        "home.light.set!",
        "home.*",
    ] {
        assert!(Capability::parse(bad).is_err(), "{bad}");
    }
}

#[test]
fn guests_get_music_lights_and_simple_things() {
    for cap in [
        "media.music.play",
        "home.light.set",
        "info.general.read",
        "risk.home",
    ] {
        assert_eq!(
            verdict(&[cap], Role::Anonymous, Strength::None),
            Verdict::Allow,
            "{cap}"
        );
        assert_eq!(
            verdict(&[cap], Role::Guest, Strength::None),
            Verdict::Allow,
            "{cap}"
        );
    }
}

#[test]
fn guests_are_denied_everything_personal_or_complex() {
    for cap in [
        "home.lock.unlock",
        "people.presence.read",
        "comm.message.send",
        "files.document.read",
        "commerce.purchase.make",
        "system.admin.manage",
        "sentinel.log.read",
        "risk.personal",
    ] {
        assert_eq!(
            verdict(&[cap], Role::Guest, Strength::Strong),
            Verdict::Deny("guest"),
            "{cap}"
        );
    }
}

#[test]
fn unlocking_needs_strong_proof_even_for_the_owner() {
    assert_eq!(
        verdict(&["home.lock.unlock"], Role::Owner, Strength::Single),
        Verdict::NeedProof(Strength::Strong)
    );
    assert_eq!(
        verdict(&["home.lock.unlock"], Role::Owner, Strength::Strong),
        Verdict::Allow
    );
}

#[test]
fn unknown_capabilities_fall_back_to_critical() {
    assert_eq!(
        verdict(&["zzz.unknown.thing"], Role::Owner, Strength::Single),
        Verdict::NeedProof(Strength::Strong)
    );
    assert_eq!(
        verdict(&["zzz.unknown.thing"], Role::Family, Strength::Strong),
        Verdict::Deny("role")
    );
}

#[test]
fn the_riskiest_capability_decides() {
    assert_eq!(
        verdict(
            &["home.light.set", "home.lock.unlock"],
            Role::Guest,
            Strength::None
        ),
        Verdict::Deny("guest")
    );
    assert_eq!(
        verdict(&[], Role::Owner, Strength::Strong),
        Verdict::Deny("role")
    );
}

#[test]
fn room_and_ownership_limits_apply() {
    let matrix = Matrix::builtin().ok();
    let lights = caps(&["home.light.set"]);
    let away = Request {
        capabilities: &lights,
        role: Role::Guest,
        strength: Strength::None,
        local: Some(false),
        own: false,
    };
    assert_eq!(
        matrix.as_ref().map(|m| decide(&away, m)),
        Some(Verdict::Deny("room"))
    );
    let health = caps(&["people.health.read"]);
    let own = Request {
        capabilities: &health,
        role: Role::Family,
        strength: Strength::Single,
        local: None,
        own: true,
    };
    let other = Request {
        own: false,
        ..own.clone()
    };
    assert_eq!(
        matrix.as_ref().map(|m| decide(&own, m)),
        Some(Verdict::Allow)
    );
    assert_eq!(
        matrix.as_ref().map(|m| decide(&other, m)),
        Some(Verdict::Deny("owner_data"))
    );
}

#[test]
fn confirmations_need_a_recognized_speaker() {
    assert_eq!(
        verdict(&["home.automation.run"], Role::Family, Strength::Weak),
        Verdict::NeedProof(Strength::Single)
    );
    assert_eq!(
        verdict(&["home.automation.run"], Role::Family, Strength::Single),
        Verdict::Confirm
    );
}

#[test]
fn the_system_principal_bypasses_the_matrix() {
    assert_eq!(
        verdict(&["system.admin.manage"], Role::System, Strength::None),
        Verdict::Allow
    );
}

#[test]
fn unknown_roles_are_anonymous() {
    assert_eq!(Role::parse("hacker"), Role::Anonymous);
    assert_eq!(Role::parse("friend"), Role::Staff);
}
