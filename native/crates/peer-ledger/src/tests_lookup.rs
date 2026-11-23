use crate::lookup::{BROADCAST_WAIT_MS, PEER_WAIT_MS, TOTAL_MS};
use crate::*;
use nuxiva_peer_core::{PeerKey, TrustBook};

const NOW: i64 = 1_700_000_000_000;

fn key(n: u8) -> PeerKey {
    PeerKey::from_seed(&[n; 32]).expect("key")
}

fn ledger(keys: &[&PeerKey]) -> Ledger {
    let mut ledger = Ledger::new(TrustBook::new());
    for k in keys {
        ledger.enroll(k.id()).expect("enroll");
    }
    ledger
}

fn addr(n: u8) -> Vec<String> {
    vec![format!("192.168.1.{n}:8443")]
}

#[test]
fn wire_round_trips_and_rejects_bad_input() {
    let a = key(1);
    let mut l = ledger(&[&a]);
    let block = l.announce(&a, addr(10), NOW).expect("ok").expect("block");
    for wire in [
        Wire::Want {
            id: a.id().to_owned(),
        },
        Wire::Have {
            block: block.clone(),
        },
        l.digest_request(),
        Wire::Delta {
            blocks: vec![block],
        },
    ] {
        assert_eq!(
            Wire::decode(&wire.encode().expect("enc")).expect("dec"),
            wire
        );
    }
    for bad in [
        &b"{"[..],
        br#"{"t":"want","id":"zz"}"#,
        br#"{"t":"want","id":"x","extra":1}"#,
        br#"{"t":"unknown"}"#,
    ] {
        assert!(Wire::decode(bad).is_err());
    }
    assert_eq!(
        Wire::decode(&vec![b' '; wire::MAX_WIRE + 1]),
        Err(LedgerError::Limit)
    );
}

#[test]
fn a_node_answers_only_what_it_knows() {
    let (a, b) = (key(1), key(2));
    let mut l = ledger(&[&a, &b]);
    l.announce(&a, addr(10), NOW).expect("ok");
    assert!(matches!(
        l.answer(&Wire::Want {
            id: a.id().to_owned()
        }),
        Some(Wire::Have { .. })
    ));
    assert_eq!(
        l.answer(&Wire::Want {
            id: b.id().to_owned()
        }),
        None
    );
    assert!(
        l.answer(&Wire::Have {
            block: l.latest(a.id()).expect("b").clone()
        })
        .is_none()
    );
}

#[test]
fn forged_replies_never_change_the_ledger() {
    let (a, stranger) = (key(1), key(9));
    let mut l = ledger(&[&a]);
    let fake = Block::seal(&stranger, 0, block::GENESIS, NOW, addr(66)).expect("seal");
    let report = l.absorb(Wire::Have { block: fake }, NOW);
    assert_eq!((report.applied, report.rejected), (0, 1));
    assert!(l.is_empty());
}

#[test]
fn cached_address_is_dialed_first_and_connects() {
    let a = key(1);
    let mut finder = ledger(&[&a]);
    finder.announce(&a, addr(10), NOW).expect("ok");
    let mut lookup = Lookup::new(a.id(), NOW);
    let Action::Dial(target) = lookup.next(&finder, &[], NOW) else {
        panic!("expected dial")
    };
    assert_eq!(target, "192.168.1.10:8443");
    lookup.dialed(&mut finder, &target, true);
    assert_eq!(lookup.next(&finder, &[], NOW), Action::Connected);
}

#[test]
fn ip_change_is_found_through_the_broadcast_answer() {
    let (a, b) = (key(1), key(2));
    let mut owner = ledger(&[&a, &b]);
    let mut finder = ledger(&[&a, &b]);
    let old = owner.announce(&a, addr(10), NOW).expect("ok").expect("blk");
    finder.accept(old, NOW).expect("old");
    owner.announce(&a, addr(77), NOW + 1_000).expect("ok");
    let mut lookup = Lookup::new(a.id(), NOW + 2_000);
    let mut now = NOW + 2_000;
    let Action::Dial(stale) = lookup.next(&finder, &[], now) else {
        panic!("dial")
    };
    lookup.dialed(&mut finder, &stale, false);
    let Action::Broadcast(want) = lookup.next(&finder, &[], now) else {
        panic!("broadcast")
    };
    let reply = owner.answer(&want).expect("owner knows itself");
    assert_eq!(finder.absorb(reply, now).applied, 1);
    now += 50;
    let Action::Dial(fresh) = lookup.next(&finder, &[], now) else {
        panic!("dial new")
    };
    assert_eq!(fresh, "192.168.1.77:8443");
    lookup.dialed(&mut finder, &fresh, true);
    assert_eq!(lookup.next(&finder, &[], now), Action::Connected);
}

#[test]
fn peers_are_asked_after_the_broadcast_goes_unanswered() {
    let (a, b) = (key(1), key(2));
    let mut owner = ledger(&[&a, &b]);
    let mut helper = ledger(&[&a, &b]);
    let mut finder = ledger(&[&a, &b]);
    let block = owner.announce(&a, addr(55), NOW).expect("ok").expect("blk");
    helper.accept(block, NOW).expect("helper");
    let peers = vec!["10.0.0.9:8443".to_owned()];
    let mut lookup = Lookup::new(a.id(), NOW);
    assert!(matches!(
        lookup.next(&finder, &peers, NOW),
        Action::Broadcast(_)
    ));
    let Action::Wait { until } = lookup.next(&finder, &peers, NOW + 10) else {
        panic!("wait")
    };
    assert_eq!(until, NOW + BROADCAST_WAIT_MS);
    let now = NOW + BROADCAST_WAIT_MS;
    let Action::Query { peer, wire } = lookup.next(&finder, &peers, now) else {
        panic!("query")
    };
    assert_eq!(peer, "10.0.0.9:8443");
    finder.absorb(helper.answer(&wire).expect("answer"), now);
    assert_eq!(
        lookup.next(&finder, &peers, now),
        Action::Dial("192.168.1.55:8443".to_owned())
    );
}

#[test]
fn nobody_knows_so_the_lookup_gives_up_and_never_loops() {
    let a = key(1);
    let finder = ledger(&[&a]);
    let peers = vec!["10.0.0.9:8443".to_owned(), "10.0.0.10:8443".to_owned()];
    let mut lookup = Lookup::new(a.id(), NOW);
    let mut now = NOW;
    let mut broadcasts = 0;
    let mut queries = 0;
    for _ in 0..40 {
        match lookup.next(&finder, &peers, now) {
            Action::Broadcast(_) => broadcasts += 1,
            Action::Query { .. } => queries += 1,
            Action::Wait { until } => now = until,
            Action::GiveUp => break,
            other => panic!("unexpected {other:?}"),
        }
    }
    assert_eq!((broadcasts, queries), (1, 2));
    assert_eq!(
        lookup.next(&finder, &peers, now + PEER_WAIT_MS),
        Action::GiveUp
    );
    assert_eq!(
        lookup.next(&finder, &peers, NOW + TOTAL_MS + 1),
        Action::GiveUp
    );
}

#[test]
fn every_candidate_is_tried_once_and_failures_are_remembered() {
    let a = key(1);
    let mut finder = ledger(&[&a]);
    let addrs = vec!["192.168.1.10:8443".to_owned(), "10.0.0.2:8443".to_owned()];
    finder.announce(&a, addrs.clone(), NOW).expect("ok");
    let mut lookup = Lookup::new(a.id(), NOW);
    let mut dialed = Vec::new();
    while let Action::Dial(target) = lookup.next(&finder, &[], NOW) {
        lookup.dialed(&mut finder, &target, false);
        dialed.push(target);
    }
    assert_eq!(dialed, addrs);
    assert_eq!(finder.candidates(a.id()), addrs);
}

#[test]
fn reconnect_backoff_grows_is_capped_and_jittered() {
    let delays: Vec<u64> = (0..8).map(|n| reconnect_delay_ms(n, 0)).collect();
    assert_eq!(delays[0], 1_000);
    assert!(delays.windows(2).all(|w| w[0] <= w[1]));
    assert_eq!(delays[7], lookup::BACKOFF_CAP_MS);
    assert!(reconnect_delay_ms(30, u64::MAX) < lookup::BACKOFF_CAP_MS * 2);
    assert_ne!(reconnect_delay_ms(3, 7), reconnect_delay_ms(3, 8));
}

#[test]
fn digest_exchange_over_the_wire_converges() {
    let (a, b) = (key(1), key(2));
    let mut left = ledger(&[&a, &b]);
    let mut right = ledger(&[&a, &b]);
    left.announce(&a, addr(10), NOW).expect("ok");
    right.announce(&b, addr(20), NOW).expect("ok");
    let to_right = left.answer(&right.digest_request()).expect("delta");
    let to_left = right.answer(&left.digest_request()).expect("delta");
    right.absorb(
        Wire::decode(&to_right.encode().expect("e")).expect("d"),
        NOW,
    );
    left.absorb(to_left, NOW);
    assert_eq!(left.digest(), right.digest());
    assert!(left.answer(&right.digest_request()).is_none());
}
