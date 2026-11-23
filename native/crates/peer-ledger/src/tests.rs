use crate::chain::MAX_BLOCKS;
use crate::*;
use nuxiva_peer_core::{PeerKey, TrustBook};

const NOW: i64 = 1_700_000_000_000;

fn key(n: u8) -> PeerKey {
    PeerKey::from_seed(&[n; 32]).expect("key")
}

fn ledger_for(keys: &[&PeerKey]) -> Ledger {
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
fn announce_chains_blocks_by_hash() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    let first = ledger
        .announce(&a, addr(10), NOW)
        .expect("ok")
        .expect("block");
    let second = ledger
        .announce(&a, addr(11), NOW + 1)
        .expect("ok")
        .expect("block");
    assert_eq!((first.index, second.index), (0, 1));
    assert_eq!(first.prev, block::GENESIS);
    assert_eq!(second.prev, first.hash());
    assert_eq!(ledger.latest(a.id()), Some(&second));
}

#[test]
fn unchanged_addresses_do_not_grow_the_log() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    ledger.announce(&a, addr(10), NOW).expect("ok");
    assert_eq!(ledger.announce(&a, addr(10), NOW + 5).expect("ok"), None);
    assert_eq!(ledger.chain(a.id()).expect("chain").blocks().count(), 1);
}

#[test]
fn untrusted_author_is_refused_everywhere() {
    let (a, stranger) = (key(1), key(2));
    let mut ledger = ledger_for(&[&a]);
    assert_eq!(
        ledger.announce(&stranger, addr(10), NOW),
        Err(LedgerError::Untrusted)
    );
    let foreign = Block::seal(&stranger, 0, block::GENESIS, NOW, addr(10)).expect("seal");
    assert_eq!(ledger.accept(foreign, NOW), Err(LedgerError::Untrusted));
}

#[test]
fn tampered_blocks_are_rejected() {
    let a = key(1);
    let mut source = ledger_for(&[&a]);
    let mut target = ledger_for(&[&a]);
    let block = source
        .announce(&a, addr(10), NOW)
        .expect("ok")
        .expect("block");
    let mut forged = block.clone();
    forged.addrs = addr(99);
    assert_eq!(target.accept(forged, NOW), Err(LedgerError::Signature));
    let mut moved = block.clone();
    moved.index = 5;
    assert_eq!(target.accept(moved, NOW), Err(LedgerError::Signature));
    assert_eq!(target.accept(block, NOW), Ok(true));
}

#[test]
fn invalid_shapes_are_rejected() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    let good = Block::seal(&a, 0, block::GENESIS, NOW, addr(10)).expect("seal");
    for bad in [
        Block {
            prev: "zz".into(),
            ..good.clone()
        },
        Block {
            sig: "00".into(),
            ..good.clone()
        },
        Block {
            ts: -1,
            ..good.clone()
        },
        Block {
            addrs: vec![],
            ..good.clone()
        },
        Block {
            addrs: vec!["0.0.0.0:80".into()],
            ..good.clone()
        },
        Block {
            author: "nope".into(),
            ..good.clone()
        },
    ] {
        assert!(ledger.accept(bad, NOW).is_err());
    }
    assert!(Block::seal(&a, 0, block::GENESIS, NOW, vec!["http://x:1".into()]).is_err());
}

#[test]
fn gaps_links_forks_and_clock_are_detected() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    let b0 = Block::seal(&a, 0, block::GENESIS, NOW, addr(10)).expect("seal");
    let b1 = Block::seal(&a, 1, &b0.hash(), NOW + 1, addr(11)).expect("seal");
    let b2 = Block::seal(&a, 2, &b1.hash(), NOW + 2, addr(12)).expect("seal");
    assert_eq!(ledger.accept(b0.clone(), NOW), Ok(true));
    assert_eq!(ledger.accept(b2.clone(), NOW), Err(LedgerError::Gap));
    let wrong = Block::seal(&a, 1, block::GENESIS, NOW + 1, addr(11)).expect("seal");
    assert_eq!(ledger.accept(wrong, NOW), Err(LedgerError::Link));
    let back = Block::seal(&a, 1, &b0.hash(), NOW - 1, addr(11)).expect("seal");
    assert_eq!(ledger.accept(back, NOW), Err(LedgerError::Clock));
    let future = Block::seal(&a, 1, &b0.hash(), NOW + 3_600_000, addr(11)).expect("seal");
    assert_eq!(ledger.accept(future, NOW), Err(LedgerError::Clock));
    assert_eq!(ledger.accept(b1.clone(), NOW), Ok(true));
    assert_eq!(ledger.accept(b1.clone(), NOW), Ok(false));
    let twin = Block::seal(&a, 1, &b0.hash(), NOW + 1, addr(77)).expect("seal");
    assert_eq!(ledger.accept(twin, NOW), Err(LedgerError::Fork));
    assert_eq!(ledger.accept(b2, NOW), Ok(true));
}

#[test]
fn chain_keeps_a_bounded_window_and_still_links() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    for i in 0..74u8 {
        ledger
            .announce(&a, addr(i.saturating_add(1)), NOW + i64::from(i))
            .expect("ok");
    }
    let chain = ledger.chain(a.id()).expect("chain");
    assert_eq!(chain.blocks().count(), MAX_BLOCKS);
    assert_eq!(chain.base_index(), Some(10));
    let mut fresh = ledger_for(&[&a]);
    let report = fresh.merge(chain.blocks().cloned().collect(), NOW + 1_000);
    assert_eq!(report.applied, MAX_BLOCKS);
    assert_eq!(fresh.latest(a.id()), ledger.latest(a.id()));
}

#[test]
fn sync_exchanges_only_what_the_peer_misses() {
    let (a, b) = (key(1), key(2));
    let mut left = ledger_for(&[&a, &b]);
    let mut right = ledger_for(&[&a, &b]);
    left.announce(&a, addr(10), NOW).expect("ok");
    left.announce(&a, addr(11), NOW + 1).expect("ok");
    right.announce(&b, addr(20), NOW).expect("ok");
    let to_right = left.missing_for(&right.digest());
    assert_eq!(to_right.len(), 2);
    let to_left = right.missing_for(&left.digest());
    assert_eq!(to_left.len(), 1);
    assert_eq!(right.merge(to_right, NOW + 2).applied, 2);
    assert_eq!(left.merge(to_left, NOW + 2).applied, 1);
    assert_eq!(left.digest(), right.digest());
    assert!(left.missing_for(&right.digest()).is_empty());
    let again = right.merge(left.missing_for(&[]), NOW + 3);
    assert_eq!((again.applied, again.rejected), (0, 0));
}

#[test]
fn merge_counts_rejections_without_poisoning_good_blocks() {
    let (a, stranger) = (key(1), key(9));
    let mut source = ledger_for(&[&a]);
    let mut target = ledger_for(&[&a]);
    let good = source
        .announce(&a, addr(10), NOW)
        .expect("ok")
        .expect("block");
    let bad = Block::seal(&stranger, 0, block::GENESIS, NOW, addr(10)).expect("seal");
    let report = target.merge(vec![bad, good], NOW);
    assert_eq!((report.applied, report.rejected), (1, 1));
}

#[test]
fn candidates_demote_failures_and_recover() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    let addrs = vec!["192.168.1.10:8443".to_owned(), "10.0.0.2:8443".to_owned()];
    ledger.announce(&a, addrs.clone(), NOW).expect("ok");
    assert_eq!(ledger.candidates(a.id()), addrs);
    ledger.report_failure(a.id(), &addrs[0]);
    assert_eq!(
        ledger.candidates(a.id()),
        vec![addrs[1].clone(), addrs[0].clone()]
    );
    ledger.report_success(a.id(), &addrs[0]);
    assert_eq!(ledger.candidates(a.id()), addrs);
    assert!(ledger.candidates("missing").is_empty());
}

#[test]
fn revoking_drops_history_and_future_blocks() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    let block = ledger
        .announce(&a, addr(10), NOW)
        .expect("ok")
        .expect("block");
    assert!(ledger.revoke(a.id()));
    assert!(ledger.is_empty());
    assert_eq!(ledger.accept(block, NOW), Err(LedgerError::Untrusted));
}

#[test]
fn authors_are_capped() {
    let mut ledger = Ledger::new(TrustBook::new());
    let mut accepted = 0usize;
    for n in 0..=255u8 {
        for m in 0..2u8 {
            let mut seed = [0u8; 32];
            seed[0] = n;
            seed[1] = m;
            let k = PeerKey::from_seed(&seed).expect("key");
            if ledger.enroll(k.id()).is_ok() && ledger.announce(&k, addr(1), NOW).is_ok() {
                accepted += 1;
            }
        }
    }
    assert!(accepted <= ledger::MAX_AUTHORS);
    assert!(ledger.len() <= ledger::MAX_AUTHORS);
}

#[test]
fn snapshot_round_trips_and_detects_corruption() {
    let (a, b) = (key(1), key(2));
    let mut ledger = ledger_for(&[&a, &b]);
    ledger.announce(&a, addr(10), NOW).expect("ok");
    ledger.announce(&a, addr(11), NOW + 1).expect("ok");
    ledger.announce(&b, addr(20), NOW).expect("ok");
    let bytes = store::encode(&ledger).expect("encode");
    let mut trust = TrustBook::new();
    trust.enroll(a.id()).expect("enroll");
    trust.enroll(b.id()).expect("enroll");
    let restored = store::decode(trust.clone(), &bytes, NOW + 2).expect("decode");
    assert_eq!(restored.digest(), ledger.digest());
    let text = String::from_utf8(bytes.clone()).expect("utf8");
    let broken = text.replace("192.168.1.11", "192.168.1.12");
    assert_eq!(
        store::decode(trust.clone(), broken.as_bytes(), NOW).err(),
        Some(LedgerError::Corrupt)
    );
    assert_eq!(
        store::decode(trust.clone(), b"{", NOW).err(),
        Some(LedgerError::Corrupt)
    );
    let mut only_a = TrustBook::new();
    only_a.enroll(a.id()).expect("enroll");
    assert_eq!(
        store::decode(only_a, &bytes, NOW).err(),
        Some(LedgerError::Corrupt)
    );
}

#[test]
fn file_store_is_atomic_private_and_survives_restart() {
    let a = key(1);
    let mut ledger = ledger_for(&[&a]);
    ledger.announce(&a, addr(10), NOW).expect("ok");
    let dir = std::env::temp_dir().join(format!("nuxiva-ledger-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("dir");
    let path = dir.join("ledger.json");
    let mut trust = TrustBook::new();
    trust.enroll(a.id()).expect("enroll");
    assert!(
        store::load(trust.clone(), &path, NOW)
            .expect("empty")
            .is_empty()
    );
    store::save(&ledger, &path).expect("save");
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = std::fs::metadata(&path).expect("meta").permissions().mode();
        assert_eq!(mode & 0o777, 0o600);
    }
    assert!(!path.with_extension("tmp").exists());
    let restored = store::load(trust, &path, NOW + 1).expect("load");
    assert_eq!(restored.digest(), ledger.digest());
    std::fs::remove_dir_all(&dir).expect("cleanup");
}

#[test]
fn error_codes_are_translation_keys() {
    for error in [
        LedgerError::Field,
        LedgerError::Limit,
        LedgerError::Untrusted,
        LedgerError::Signature,
        LedgerError::Link,
        LedgerError::Gap,
        LedgerError::Fork,
        LedgerError::Clock,
        LedgerError::Capacity,
        LedgerError::Storage,
        LedgerError::Corrupt,
    ] {
        assert!(error.code().starts_with("ledger.error."));
    }
}
