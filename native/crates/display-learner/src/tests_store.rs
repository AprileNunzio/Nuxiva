use crate::error::LearnError;
use crate::store::{open, seal};

const ANNA: &str = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90";
const LUCA: &str = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0";
const MASTER: [u8; 32] = [7; 32];

#[test]
fn sealed_profiles_open_only_for_their_owner() {
    let Ok(blob) = seal(&MASTER, ANNA, b"{\"models\":{}}") else {
        unreachable!()
    };
    assert!(!blob.windows(6).any(|w| w == b"models"));
    assert_eq!(
        open(&MASTER, ANNA, &blob).map(|p| p.to_vec()),
        Ok(b"{\"models\":{}}".to_vec())
    );
    assert_eq!(
        open(&MASTER, LUCA, &blob).map(|p| p.to_vec()),
        Err(LearnError::Crypto)
    );
    assert_eq!(
        open(&[8; 32], ANNA, &blob).map(|p| p.to_vec()),
        Err(LearnError::Crypto)
    );
}

#[test]
fn tampering_and_bad_keys_are_rejected() {
    let Ok(mut blob) = seal(&MASTER, ANNA, b"hello") else {
        unreachable!()
    };
    if let Some(last) = blob.last_mut() {
        *last ^= 1;
    }
    assert_eq!(
        open(&MASTER, ANNA, &blob).map(|p| p.to_vec()),
        Err(LearnError::Crypto)
    );
    assert_eq!(
        open(&MASTER, ANNA, b"NXLRN1\nshort").map(|p| p.to_vec()),
        Err(LearnError::Corrupt)
    );
    assert_eq!(seal(&[0; 32], ANNA, b"x"), Err(LearnError::Crypto));
    assert_eq!(seal(&[1; 16], ANNA, b"x"), Err(LearnError::Crypto));
    assert_eq!(seal(&MASTER, "bad", b"x"), Err(LearnError::InvalidPerson));
}

#[test]
fn every_seal_uses_a_fresh_nonce() {
    let (Ok(a), Ok(b)) = (seal(&MASTER, ANNA, b"same"), seal(&MASTER, ANNA, b"same")) else {
        unreachable!()
    };
    assert_ne!(a, b);
}
