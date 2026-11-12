use crate::{Fernet, SealError, generate_key};

const KEY: &str = "cw_0x689RpI-jtRR7oE8h_eQsKImvJapLeSbXpwF4e4=";
const SPEC_TOKEN: &str = "gAAAAAAdwJ6wAAECAwQFBgcICQoLDA0ODy021cpGVWKZ_eEwCGM4BLLF_5CV9dOPmrhuVUPgJobwOz7JcbmrR64jVmpU4IwqDA==";

#[test]
fn spec_vector_round_trips() -> Result<(), SealError> {
    let fernet = Fernet::new(KEY.as_bytes())?;
    let iv: [u8; 16] = core::array::from_fn(|i| u8::try_from(i).unwrap_or_default());
    let token = fernet.encrypt_with_iv(b"hello", 499_162_800, iv)?;
    assert_eq!(token, SPEC_TOKEN);
    assert_eq!(
        fernet.decrypt(SPEC_TOKEN.as_bytes(), Some(60), 499_162_860)?,
        b"hello"
    );
    assert_eq!(
        fernet.decrypt(SPEC_TOKEN.as_bytes(), None, 2_000_000_000)?,
        b"hello"
    );
    Ok(())
}

#[test]
fn ttl_and_skew_are_enforced() -> Result<(), SealError> {
    let fernet = Fernet::new(KEY.as_bytes())?;
    let token = fernet.encrypt(b"x", 1_000)?;
    assert!(fernet.decrypt(token.as_bytes(), Some(10), 1_011).is_err());
    assert!(fernet.decrypt(token.as_bytes(), Some(10), 900).is_err());
    assert_eq!(fernet.decrypt(token.as_bytes(), Some(10), 1_010)?, b"x");
    Ok(())
}

#[test]
fn tampering_and_wrong_keys_fail() -> Result<(), SealError> {
    let fernet = Fernet::new(KEY.as_bytes())?;
    let other = Fernet::new(generate_key()?.as_bytes())?;
    let token = fernet.encrypt(b"segreto", 5)?;
    assert!(other.decrypt(token.as_bytes(), None, 5).is_err());
    let mut bytes = token.into_bytes();
    if let Some(b) = bytes.get_mut(30) {
        *b = if *b == b'A' { b'B' } else { b'A' };
    }
    assert!(fernet.decrypt(&bytes, None, 5).is_err());
    assert!(fernet.decrypt(b"", None, 5).is_err());
    assert!(fernet.decrypt(b"gAAAA", None, 5).is_err());
    assert!(Fernet::new(b"short").is_err());
    assert!(Fernet::new(format!("{KEY}\n").as_bytes()).is_ok());
    assert_eq!(
        fernet.decrypt(fernet.encrypt(b"", 5)?.as_bytes(), None, 5)?,
        b""
    );
    Ok(())
}
