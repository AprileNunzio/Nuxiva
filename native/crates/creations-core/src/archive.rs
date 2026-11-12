use rusqlite::{Connection, OptionalExtension, params};
use serde::{Deserialize, Serialize};
use std::fmt;
use std::path::Path;

use crate::text::{shard, tokens};

pub const MAX_LIMIT: usize = 100;
const MAX_KEY: usize = 120;
const MAX_KIND: usize = 32;
const MAX_META: usize = 16 * 1024;
const MAX_TAGS: usize = 48;
const MAX_QUERY_TOKENS: usize = 8;

#[derive(Debug)]
pub struct ArchiveError(pub String);

impl fmt::Display for ArchiveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for ArchiveError {}

impl From<rusqlite::Error> for ArchiveError {
    fn from(e: rusqlite::Error) -> Self {
        Self(e.to_string())
    }
}

fn bad(message: &str) -> ArchiveError {
    ArchiveError(message.to_owned())
}

#[derive(Debug, Clone, Default, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct NewEntry {
    pub key: String,
    pub digest: String,
    pub kind: String,
    pub meta: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Entry {
    pub key: String,
    pub digest: String,
    pub kind: String,
    pub meta: String,
    pub created: i64,
    pub last: i64,
    pub uses: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Hit {
    pub key: String,
    pub digest: String,
    pub kind: String,
    pub uses: i64,
}

#[derive(Debug)]
pub struct Archive {
    conn: Connection,
}

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS creations (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    digest TEXT NOT NULL,
    kind TEXT NOT NULL,
    meta TEXT NOT NULL,
    created INTEGER NOT NULL,
    last INTEGER NOT NULL,
    uses INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS creations_last ON creations(last);
CREATE INDEX IF NOT EXISTS creations_digest ON creations(digest);
CREATE VIRTUAL TABLE IF NOT EXISTS creations_fts USING fts5(
    key, tags, content='', contentless_delete=1,
    tokenize='unicode61 remove_diacritics 2', prefix='2 3'
);";

fn entry(row: &rusqlite::Row<'_>) -> rusqlite::Result<Entry> {
    Ok(Entry {
        key: row.get(0)?,
        digest: row.get(1)?,
        kind: row.get(2)?,
        meta: row.get(3)?,
        created: row.get(4)?,
        last: row.get(5)?,
        uses: row.get(6)?,
    })
}

const COLUMNS: &str = "key, digest, kind, meta, created, last, uses";

impl Archive {
    fn init(conn: Connection) -> Result<Self, ArchiveError> {
        conn.execute_batch(
            "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA trusted_schema=OFF; PRAGMA secure_delete=ON;",
        )?;
        conn.execute_batch(SCHEMA)?;
        Ok(Self { conn })
    }

    pub fn open(path: &Path) -> Result<Self, ArchiveError> {
        let conn = Connection::open(path)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))
                .map_err(|e| ArchiveError(e.to_string()))?;
        }
        Self::init(conn)
    }

    pub fn open_memory() -> Result<Self, ArchiveError> {
        Self::init(Connection::open_in_memory()?)
    }

    fn check(new: &NewEntry) -> Result<(), ArchiveError> {
        if new.key.is_empty() || new.key.chars().count() > MAX_KEY {
            return Err(bad("invalid key"));
        }
        if shard(&new.digest).is_none() {
            return Err(bad("invalid digest"));
        }
        if new.kind.is_empty() || new.kind.len() > MAX_KIND || new.meta.len() > MAX_META {
            return Err(bad("invalid entry"));
        }
        Ok(())
    }

    pub fn put(&mut self, new: &NewEntry, now: i64) -> Result<Entry, ArchiveError> {
        Self::check(new)?;
        let tags: Vec<String> = new
            .tags
            .iter()
            .take(MAX_TAGS)
            .flat_map(|t| tokens(t, MAX_TAGS))
            .collect();
        let words = tokens(&new.key, MAX_TAGS).join(" ");
        let tx = self.conn.transaction()?;
        let existing: Option<(i64, i64, i64)> = tx
            .query_row(
                "SELECT id, created, uses FROM creations WHERE key = ?1",
                [&new.key],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
            )
            .optional()?;
        let (id, created, uses) = if let Some((id, created, uses)) = existing {
            tx.execute(
                "UPDATE creations SET digest=?1, kind=?2, meta=?3, last=?4 WHERE id=?5",
                params![new.digest, new.kind, new.meta, now, id],
            )?;
            tx.execute("DELETE FROM creations_fts WHERE rowid = ?1", [id])?;
            (id, created, uses)
        } else {
            tx.execute(
                "INSERT INTO creations(key, digest, kind, meta, created, last, uses) VALUES (?1,?2,?3,?4,?5,?5,1)",
                params![new.key, new.digest, new.kind, new.meta, now],
            )?;
            (tx.last_insert_rowid(), now, 1)
        };
        tx.execute(
            "INSERT INTO creations_fts(rowid, key, tags) VALUES (?1, ?2, ?3)",
            params![id, words, tags.join(" ")],
        )?;
        tx.commit()?;
        Ok(Entry {
            key: new.key.clone(),
            digest: new.digest.clone(),
            kind: new.kind.clone(),
            meta: new.meta.clone(),
            created,
            last: now,
            uses,
        })
    }

    pub fn lookup(&mut self, key: &str, now: i64) -> Result<Option<Entry>, ArchiveError> {
        let tx = self.conn.transaction()?;
        tx.execute(
            "UPDATE creations SET uses = uses + 1, last = ?2 WHERE key = ?1",
            params![key, now],
        )?;
        let found = tx
            .query_row(
                &format!("SELECT {COLUMNS} FROM creations WHERE key = ?1"),
                [key],
                entry,
            )
            .optional()?;
        tx.commit()?;
        Ok(found)
    }

    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<Hit>, ArchiveError> {
        let words = tokens(query, MAX_QUERY_TOKENS);
        if words.is_empty() {
            return Ok(Vec::new());
        }
        let expression = words
            .iter()
            .map(|w| format!("\"{w}\"*"))
            .collect::<Vec<_>>()
            .join(" OR ");
        let cap = i64::try_from(limit.clamp(1, MAX_LIMIT)).unwrap_or(10);
        let mut stmt = self.conn.prepare_cached(
            "SELECT c.key, c.digest, c.kind, c.uses
             FROM (SELECT rowid AS id, rank FROM creations_fts WHERE creations_fts MATCH ?1 LIMIT 2000) f
             JOIN creations c ON c.id = f.id ORDER BY f.rank, c.uses DESC, c.key LIMIT ?2",
        )?;
        let rows = stmt.query_map(params![expression, cap], |r| {
            Ok(Hit {
                key: r.get(0)?,
                digest: r.get(1)?,
                kind: r.get(2)?,
                uses: r.get(3)?,
            })
        })?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    pub fn recent(&self, limit: usize) -> Result<Vec<Entry>, ArchiveError> {
        let cap = i64::try_from(limit.clamp(1, MAX_LIMIT)).unwrap_or(10);
        let mut stmt = self.conn.prepare_cached(&format!(
            "SELECT {COLUMNS} FROM creations ORDER BY last DESC, key LIMIT ?1"
        ))?;
        let rows = stmt.query_map([cap], entry)?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    pub fn count(&self) -> Result<u64, ArchiveError> {
        let n: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM creations", [], |r| r.get(0))?;
        Ok(u64::try_from(n).unwrap_or(0))
    }

    pub fn evict(&mut self, keep: usize) -> Result<Vec<String>, ArchiveError> {
        let keep = i64::try_from(keep).unwrap_or(i64::MAX);
        let tx = self.conn.transaction()?;
        let victims: Vec<(i64, String)> = {
            let mut stmt = tx.prepare(
                "SELECT id, digest FROM creations ORDER BY last DESC, key LIMIT -1 OFFSET ?1",
            )?;
            let rows = stmt.query_map([keep], |r| Ok((r.get(0)?, r.get(1)?)))?;
            rows.collect::<Result<Vec<_>, _>>()?
        };
        for (id, _) in &victims {
            tx.execute("DELETE FROM creations_fts WHERE rowid = ?1", [id])?;
            tx.execute("DELETE FROM creations WHERE id = ?1", [id])?;
        }
        let mut orphans: Vec<String> = Vec::new();
        for (_, digest) in victims {
            let used: i64 = tx.query_row(
                "SELECT COUNT(*) FROM creations WHERE digest = ?1",
                [&digest],
                |r| r.get(0),
            )?;
            if used == 0 && !orphans.contains(&digest) {
                orphans.push(digest);
            }
        }
        tx.commit()?;
        Ok(orphans)
    }
}
