#![allow(clippy::pedantic)]
#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic
)]

mod sim;

use nuxiva_peer_core::*;
use sim::Sim;

fn everyone_knows(sim: &Sim, subject: usize, addr: &str) -> usize {
    let id = sim.ids[subject].clone();
    sim.nodes
        .iter()
        .enumerate()
        .filter(|(i, n)| {
            n.alive
                && *i != subject
                && n.directory.candidates(&id).first().map(String::as_str) == Some(addr)
        })
        .count()
}

#[test]
fn address_change_reaches_all_nodes_and_rejoiner_catches_up() {
    let mut sim = Sim::new(100, 0x10CA_70A5);
    sim.run(20_000);
    for n in sim.nodes.iter() {
        assert_eq!(n.directory.len(), 100);
    }
    sim.kill(77);
    let movers = [21usize, 30, 45, 60, 99];
    for (k, m) in movers.iter().enumerate() {
        sim.change_address(*m, &format!("192.168.7.{}:7000", 10 + k));
    }
    sim.change_address(1, "203.0.113.5:7000");
    sim.run(8_000);
    for (k, m) in movers.iter().enumerate() {
        let addr = format!("192.168.7.{}:7000", 10 + k);
        assert!(everyone_knows(&sim, *m, &addr) >= 98, "node {m}");
    }
    assert!(everyone_knows(&sim, 1, "203.0.113.5:7000") >= 98);
    sim.nodes[77].alive = true;
    sim.run(60_000);
    for (k, m) in movers.iter().enumerate() {
        let addr = format!("192.168.7.{}:7000", 10 + k);
        let id = sim.ids[*m].clone();
        assert_eq!(
            sim.nodes[77]
                .directory
                .candidates(&id)
                .first()
                .map(String::as_str),
            Some(addr.as_str())
        );
    }
}

#[test]
fn stale_forged_and_hostile_locators_are_ignored() {
    let mut sim = Sim::new(20, 0x10CA_70A6);
    sim.run(10_000);
    let id = sim.ids[3].clone();
    let before = sim.nodes[0].directory.get(&id).expect("rec").clone();
    let stale = before.envelope.clone();
    let now = sim.now;
    let node = &mut sim.nodes[0];
    assert_eq!(node.directory.learn(&node.verifier, &stale, now), Ok(false));
    let mut forged = stale.clone();
    forged.seq += 1;
    assert_eq!(
        node.directory.learn(&node.verifier, &forged, now),
        Err(PeerError::Signature)
    );
    let intruder = PeerKey::generate().expect("key");
    let rogue = intruder
        .seal(
            1,
            now,
            3,
            &Message::Locate {
                addrs: vec!["198.51.100.9:7000".into()],
            },
        )
        .expect("seal");
    assert_eq!(
        node.directory.learn(&node.verifier, &rogue, now),
        Err(PeerError::Untrusted)
    );
    for bad in [
        "0.0.0.0:80",
        "224.0.0.1:80",
        "10.0.0.1:0",
        "http://x:80",
        "-a.b:80",
        "host",
    ] {
        assert!(addr::check_addr(bad).is_err(), "{bad}");
    }
    assert!(addr::check_addr("[2001:db8::1]:7000").is_ok());
    assert!(addr::check_addr("nodo-1.local:7000").is_ok());
    assert_eq!(node.directory.get(&id).expect("rec").seq, before.seq);
}

#[test]
fn failed_addresses_are_tried_last_and_recover() {
    let key = PeerKey::from_seed(&[9u8; 32]).expect("key");
    let mut trust = TrustBook::new();
    trust.enroll(key.id()).expect("enroll");
    let verifier = Verifier::new(trust);
    let mut dir = Directory::new();
    let env = key
        .seal(
            1,
            0,
            3,
            &Message::Locate {
                addrs: vec!["10.0.0.1:7000".into(), "192.168.1.5:7000".into()],
            },
        )
        .expect("seal");
    assert!(dir.learn(&verifier, &env, 0).expect("learn"));
    assert_eq!(dir.candidates(key.id())[0], "10.0.0.1:7000");
    dir.report_failure(key.id(), "10.0.0.1:7000");
    assert_eq!(dir.candidates(key.id())[0], "192.168.1.5:7000");
    dir.report_success(key.id(), "10.0.0.1:7000");
    assert_eq!(dir.candidates(key.id())[0], "10.0.0.1:7000");
    let newer = key
        .seal(
            2,
            0,
            3,
            &Message::Locate {
                addrs: vec!["172.16.0.9:7000".into()],
            },
        )
        .expect("seal");
    assert!(dir.learn(&verifier, &newer, 1).expect("learn"));
    assert_eq!(dir.candidates(key.id()), vec!["172.16.0.9:7000".to_owned()]);
}
