use std::fs;
use std::path::PathBuf;

use serde_json::json;

use crate::{Chain, LedgerError, LedgerKey, LedgerStore};

fn key(seed: u8) -> LedgerKey {
    LedgerKey::from_bytes([seed; 32])
}

struct Scratch(PathBuf);

impl Scratch {
    fn new(tag: &str) -> Result<Self, LedgerError> {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce)
            .map_err(|e| LedgerError::Io(std::io::Error::other(e.to_string())))?;
        let dir =
            std::env::temp_dir().join(format!("nxl-{tag}-{:016x}", u64::from_le_bytes(nonce)));
        fs::create_dir_all(&dir)?;
        Ok(Self(dir))
    }

    fn file(&self) -> PathBuf {
        self.0.join("ledger.jsonl")
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn chain_links_and_verifies() -> Result<(), LedgerError> {
    let mut writer = Chain::new(key(7));
    let a = writer.seal("project.created", json!({"id": "shop"}), 1)?;
    let b = writer.seal("task.started", json!({"id": "db"}), 2)?;
    assert_eq!(b.prev, a.mac);
    let mut reader = Chain::new(key(7));
    reader.accept(&a)?;
    reader.accept(&b)?;
    assert_eq!(reader.head(), writer.head());
    Ok(())
}

#[test]
fn tampering_is_detected() -> Result<(), LedgerError> {
    let mut writer = Chain::new(key(7));
    let a = writer.seal("x", json!({"v": 1}), 1)?;
    let mut forged = a.clone();
    forged.payload = json!({"v": 2});
    assert!(matches!(
        Chain::new(key(7)).accept(&forged),
        Err(LedgerError::Signature(0))
    ));
    assert!(matches!(
        Chain::new(key(8)).accept(&a),
        Err(LedgerError::Signature(0))
    ));
    let b = writer.seal("x", json!({}), 2)?;
    assert!(matches!(
        Chain::new(key(7)).accept(&b),
        Err(LedgerError::Sequence(1))
    ));
    Ok(())
}

#[test]
fn rejects_bad_kind_and_huge_payload() {
    let mut chain = Chain::new(key(1));
    assert!(matches!(
        chain.seal("Bad Kind", json!(null), 0),
        Err(LedgerError::InvalidKind)
    ));
    let huge = "x".repeat(300 * 1024);
    assert!(matches!(
        chain.seal("big", json!(huge), 0),
        Err(LedgerError::PayloadTooLarge(_))
    ));
    assert!(chain.is_empty());
}

#[test]
fn store_survives_reopen() -> Result<(), LedgerError> {
    let scratch = Scratch::new("reopen")?;
    let head = {
        let mut store = LedgerStore::open(&scratch.file(), key(3))?;
        store.append("a", json!({"n": 1}), 10)?;
        store.append("b", json!({"n": 2}), 11)?;
        store.chain().head()
    };
    let mut store = LedgerStore::open(&scratch.file(), key(3))?;
    assert_eq!(store.chain().len(), 2);
    assert_eq!(store.chain().head(), head);
    assert_eq!(store.append("c", json!({}), 12)?.seq, 2);
    Ok(())
}

#[cfg(unix)]
#[test]
fn store_is_private_to_owner() -> Result<(), LedgerError> {
    use std::os::unix::fs::PermissionsExt;
    let scratch = Scratch::new("mode")?;
    LedgerStore::open(&scratch.file(), key(3))?;
    assert_eq!(
        fs::metadata(scratch.file())?.permissions().mode() & 0o077,
        0
    );
    Ok(())
}

#[cfg(unix)]
#[test]
fn store_refuses_symlinks() -> Result<(), LedgerError> {
    let scratch = Scratch::new("link")?;
    let target = scratch.0.join("target");
    fs::write(&target, b"")?;
    std::os::unix::fs::symlink(&target, scratch.file())?;
    assert!(LedgerStore::open(&scratch.file(), key(3)).is_err());
    Ok(())
}

#[test]
fn store_detects_edited_file() -> Result<(), LedgerError> {
    let scratch = Scratch::new("edit")?;
    {
        let mut store = LedgerStore::open(&scratch.file(), key(4))?;
        store.append("a", json!({"amount": 10}), 1)?;
    }
    let text = fs::read_to_string(scratch.file())?.replace("10", "99");
    fs::write(scratch.file(), text)?;
    assert!(matches!(
        LedgerStore::open(&scratch.file(), key(4)),
        Err(LedgerError::Signature(0))
    ));
    Ok(())
}

#[test]
fn store_rejects_torn_tail() -> Result<(), LedgerError> {
    let scratch = Scratch::new("torn")?;
    {
        let mut store = LedgerStore::open(&scratch.file(), key(5))?;
        store.append("a", json!({}), 1)?;
    }
    let mut bytes = fs::read(scratch.file())?;
    bytes.extend_from_slice(b"{\"seq\":1");
    fs::write(scratch.file(), bytes)?;
    assert!(matches!(
        LedgerStore::open(&scratch.file(), key(5)),
        Err(LedgerError::Malformed(2))
    ));
    Ok(())
}
