use crate::block::Block;
use crate::error::{LedgerError, LedgerResult};
use crate::ledger::Ledger;
use nuxiva_peer_core::TrustBook;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::Path;

pub const MAX_FILE: usize = 16 * 1024 * 1024;
const VERSION: u8 = 1;

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Snapshot {
    v: u8,
    blocks: Vec<Block>,
}

pub fn encode(ledger: &Ledger) -> LedgerResult<Vec<u8>> {
    let blocks = ledger
        .chains
        .values()
        .flat_map(|chain| chain.blocks().cloned())
        .collect();
    let bytes =
        serde_json::to_vec(&Snapshot { v: VERSION, blocks }).map_err(|_| LedgerError::Storage)?;
    if bytes.len() > MAX_FILE {
        return Err(LedgerError::Limit);
    }
    Ok(bytes)
}

pub fn decode(trust: TrustBook, bytes: &[u8], now: i64) -> LedgerResult<Ledger> {
    if bytes.len() > MAX_FILE {
        return Err(LedgerError::Limit);
    }
    let snapshot: Snapshot = serde_json::from_slice(bytes).map_err(|_| LedgerError::Corrupt)?;
    if snapshot.v != VERSION {
        return Err(LedgerError::Corrupt);
    }
    let mut ledger = Ledger::new(trust);
    let mut blocks = snapshot.blocks;
    blocks.sort_by(|a, b| (&a.author, a.index).cmp(&(&b.author, b.index)));
    for block in blocks {
        ledger
            .accept(block, now)
            .map_err(|_| LedgerError::Corrupt)?;
    }
    Ok(ledger)
}

pub fn save(ledger: &Ledger, path: &Path) -> LedgerResult<()> {
    let bytes = encode(ledger)?;
    let temp = path.with_extension("tmp");
    write_private(&temp, &bytes).map_err(|_| LedgerError::Storage)?;
    fs::rename(&temp, path).map_err(|_| LedgerError::Storage)
}

pub fn load(trust: TrustBook, path: &Path, now: i64) -> LedgerResult<Ledger> {
    let meta = match fs::metadata(path) {
        Ok(meta) => meta,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Ledger::new(trust));
        }
        Err(_) => return Err(LedgerError::Storage),
    };
    if meta.len() > MAX_FILE as u64 {
        return Err(LedgerError::Limit);
    }
    let bytes = fs::read(path).map_err(|_| LedgerError::Storage)?;
    decode(trust, &bytes, now)
}

fn write_private(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let mut options = fs::OpenOptions::new();
    options.write(true).create(true).truncate(true);
    #[cfg(unix)]
    std::os::unix::fs::OpenOptionsExt::mode(&mut options, 0o600);
    let mut file = options.open(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}
