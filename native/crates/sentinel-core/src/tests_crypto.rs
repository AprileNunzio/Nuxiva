use crate::checkpoint;
use crate::error::SentinelError;
use crate::event::Subject;
use crate::journal::{Day, Head, append, open, verify};
use crate::keys::{new_day_key, open_day_key};
use crate::kind::Kind;
use crate::tests::{ANNA, event};

const MASTER: [u8; 32] = [9; 32];

fn day() -> Day {
    match Day::parse("2026-11-05") {
        Ok(d) => d,
        Err(e) => unreachable!("{e}"),
    }
}

fn journal(n: u64) -> (Vec<u8>, Vec<u8>, Head) {
    let d = day();
    let Ok(wrapped) = new_day_key(&MASTER, &d) else {
        unreachable!()
    };
    let Ok(key) = open_day_key(&MASTER, &d, &wrapped) else {
        unreachable!()
    };
    let mut head = Head::genesis(&d);
    let mut data = Vec::new();
    for i in 0..n {
        let Ok((frame, next)) = append(
            &key,
            &d,
            &head,
            &event(i, Kind::PresenceArrived, Subject::Person(ANNA.to_owned())),
        ) else {
            unreachable!()
        };
        data.extend_from_slice(&frame);
        head = next;
    }
    (wrapped, data, head)
}

#[test]
fn a_day_round_trips_and_hides_its_content() {
    let (wrapped, data, head) = journal(5);
    assert!(!data.windows(4).any(|w| w == b"Anna"));
    let Ok(key) = open_day_key(&MASTER, &day(), &wrapped) else {
        unreachable!()
    };
    let Ok(opened) = open(&key, &day(), &data) else {
        unreachable!()
    };
    assert_eq!(opened.count, 5);
    assert_eq!(opened.head, head.hex());
    assert!(!opened.truncated);
    assert_eq!(opened.valid_len, data.len());
}

#[test]
fn one_changed_byte_breaks_the_chain() {
    let (wrapped, mut data, _) = journal(4);
    let Ok(key) = open_day_key(&MASTER, &day(), &wrapped) else {
        unreachable!()
    };
    let mut ct = data.clone();
    if let Some(b) = ct.get_mut(4 + 32 + 24 + 5) {
        *b ^= 0x40;
    }
    assert!(matches!(
        open(&key, &day(), &ct),
        Err(SentinelError::Broken(_))
    ));
    let mut prev = data.clone();
    if let Some(b) = prev.get_mut(4 + 3) {
        *b ^= 0x01;
    }
    assert_eq!(
        verify(&day(), &prev).map(|v| v.1),
        Err(SentinelError::Broken(0))
    );
    if let Some(b) = data.get_mut(0) {
        *b = 0xff;
    }
    assert_eq!(
        verify(&day(), &data).map(|v| v.1),
        Err(SentinelError::Broken(0))
    );
}

#[test]
fn reordering_or_dropping_records_is_detected_without_the_key() {
    let (_, data, _) = journal(3);
    let head4: [u8; 4] = data
        .get(..4)
        .and_then(|b| b.try_into().ok())
        .unwrap_or_default();
    let first_len = usize::try_from(u32::from_be_bytes(head4))
        .unwrap_or(0)
        .saturating_add(4);
    let dropped = data.get(first_len..).unwrap_or_default();
    assert_eq!(verify(&day(), dropped), Err(SentinelError::Broken(0)));
}

#[test]
fn a_destroyed_or_wrong_day_key_makes_the_day_unreadable() {
    let (wrapped, data, _) = journal(2);
    assert_eq!(
        open_day_key(&[8; 32], &day(), &wrapped).map(|k| k.to_vec()),
        Err(SentinelError::Crypto)
    );
    let Ok(other) = Day::parse("2026-11-06") else {
        unreachable!()
    };
    assert_eq!(
        open_day_key(&MASTER, &other, &wrapped).map(|k| k.to_vec()),
        Err(SentinelError::Crypto)
    );
    assert!(open(&[7; 32], &day(), &data).is_err());
}

#[test]
fn a_torn_last_write_is_reported_and_skipped() {
    let (wrapped, mut data, _) = journal(3);
    let full = data.len();
    data.extend_from_slice(&[0, 0, 1, 0, 1, 2]);
    let Ok(key) = open_day_key(&MASTER, &day(), &wrapped) else {
        unreachable!()
    };
    let Ok(opened) = open(&key, &day(), &data) else {
        unreachable!()
    };
    assert!(opened.truncated);
    assert_eq!((opened.count, opened.valid_len), (3, full));
}

#[test]
fn checkpoints_are_signed_and_bound_to_the_head() {
    let (_, data, head) = journal(2);
    let seed = [5_u8; 32];
    let Ok(public) = checkpoint::public_key(&seed) else {
        unreachable!()
    };
    let Ok(sig) = checkpoint::sign(&seed, &day(), 2, &head) else {
        unreachable!()
    };
    assert!(checkpoint::verify(&public, &day(), 2, &head, &sig).is_ok());
    assert_eq!(
        checkpoint::verify(&public, &day(), 3, &head, &sig),
        Err(SentinelError::Signature)
    );
    let Ok((verified, count, _, _)) = verify(&day(), &data) else {
        unreachable!()
    };
    assert_eq!((verified, count), (head, 2));
}

#[test]
fn days_and_heads_are_validated() {
    for bad in ["2026-13-01", "2026-11-5", "../../etc", "2026-11-00"] {
        assert_eq!(Day::parse(bad), Err(SentinelError::InvalidDay));
    }
    let h = Head::genesis(&day());
    assert_eq!(Head::from_hex(&h.hex()), Ok(h));
    assert!(Head::from_hex("zz").is_err());
}
