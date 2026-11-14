use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::envelope::{Domain, Envelope, Level};
use crate::error::CollaudoError;

const MAX_CORRS: usize = 512;
const ZERO: [u8; 32] = [0; 32];

#[derive(Debug, Clone)]
pub struct StoreConfig {
    pub dir: PathBuf,
    pub segment_bytes: u64,
    pub keep_segments: usize,
    pub key: [u8; 32],
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SegmentMeta {
    pub first_seq: u64,
    pub last_seq: u64,
    pub min_ms: u64,
    pub max_ms: u64,
    pub bytes: u64,
    pub lines: u64,
    pub counts: BTreeMap<String, u64>,
    pub corrs: BTreeSet<String>,
    pub corrs_complete: bool,
    pub head_prev: Option<String>,
    pub tail_mac: String,
}

#[derive(Debug, Clone, Default)]
pub struct Query {
    pub since_seq: u64,
    pub from_ms: Option<u64>,
    pub to_ms: Option<u64>,
    pub domain: Option<Domain>,
    pub min_level: Option<Level>,
    pub corr: Option<String>,
    pub kind_prefix: Option<String>,
    pub limit: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct Integrity {
    pub segments: usize,
    pub lines: u64,
    pub ok: bool,
    pub anchored: bool,
    pub broken_segment: Option<String>,
}

#[derive(Debug)]
pub struct Store {
    cfg: StoreConfig,
    metas: Vec<(String, SegmentMeta)>,
    file: Option<File>,
    tail: [u8; 32],
    next_seq: u64,
}

fn hex(bytes: &[u8; 32]) -> String {
    blake3::Hash::from_bytes(*bytes).to_hex().to_string()
}

fn unhex(value: &str) -> Option<[u8; 32]> {
    blake3::Hash::from_hex(value).ok().map(|h| *h.as_bytes())
}

fn mac(key: &[u8; 32], prev: &[u8; 32], json: &[u8]) -> [u8; 32] {
    let mut hasher = blake3::Hasher::new_keyed(key);
    hasher.update(prev);
    hasher.update(json);
    *hasher.finalize().as_bytes()
}

fn segment_name(first_seq: u64) -> String {
    format!("seg-{first_seq:016}.jsonl")
}

fn split_line(line: &str) -> Option<(&str, &str)> {
    line.split_once('\t')
}

fn add_meta(meta: &mut SegmentMeta, env: &Envelope, line_bytes: u64, tail: &[u8; 32]) {
    if meta.lines == 0 {
        meta.first_seq = env.seq;
        meta.min_ms = env.at_ms;
        meta.corrs_complete = true;
    }
    meta.last_seq = env.seq;
    meta.min_ms = meta.min_ms.min(env.at_ms);
    meta.max_ms = meta.max_ms.max(env.at_ms);
    meta.bytes = meta.bytes.saturating_add(line_bytes);
    meta.lines = meta.lines.saturating_add(1);
    let key = format!("{}:{}", env.domain.as_str(), env.level.as_str());
    let count = meta.counts.entry(key).or_insert(0);
    *count = count.saturating_add(1);
    if let Some(corr) = &env.corr {
        if meta.corrs.len() < MAX_CORRS || meta.corrs.contains(corr) {
            meta.corrs.insert(corr.clone());
        } else {
            meta.corrs_complete = false;
        }
    }
    meta.tail_mac = hex(tail);
}

fn scan(
    path: &Path,
    key: &[u8; 32],
    prev: Option<[u8; 32]>,
) -> Result<(SegmentMeta, bool), CollaudoError> {
    let reader = BufReader::new(File::open(path)?);
    let mut meta = SegmentMeta {
        head_prev: prev.as_ref().map(hex),
        ..SegmentMeta::default()
    };
    let mut chain = prev;
    let mut ok = true;
    for line in reader.lines() {
        let line = line?;
        let Some((mac_hex, json)) = split_line(&line) else {
            ok = false;
            break;
        };
        let Some(stored) = unhex(mac_hex) else {
            ok = false;
            break;
        };
        let Ok(env) = serde_json::from_str::<Envelope>(json) else {
            ok = false;
            break;
        };
        if let Some(prev) = chain {
            if mac(key, &prev, json.as_bytes()) != stored {
                ok = false;
            }
        }
        chain = Some(stored);
        let line_bytes = u64::try_from(line.len())
            .unwrap_or(u64::MAX)
            .saturating_add(1);
        add_meta(&mut meta, &env, line_bytes, &stored);
    }
    Ok((meta, ok))
}

impl Store {
    pub fn open(cfg: StoreConfig) -> Result<Self, CollaudoError> {
        fs::create_dir_all(&cfg.dir)?;
        restrict(&cfg.dir, true)?;
        let mut names: Vec<String> = fs::read_dir(&cfg.dir)?
            .filter_map(Result::ok)
            .filter_map(|e| e.file_name().into_string().ok())
            .filter(|n| {
                n.starts_with("seg-") && Path::new(n).extension().is_some_and(|x| x == "jsonl")
            })
            .collect();
        names.sort();
        let mut metas = Vec::new();
        let mut prev: Option<[u8; 32]> = None;
        let last = names.len().saturating_sub(1);
        for (i, name) in names.iter().enumerate() {
            let path = cfg.dir.join(name);
            let idx = path.with_extension("idx");
            let cached = if i == last {
                None
            } else {
                fs::read_to_string(&idx)
                    .ok()
                    .and_then(|t| serde_json::from_str::<SegmentMeta>(&t).ok())
            };
            let meta = match cached {
                Some(meta) => meta,
                None => scan(&path, &cfg.key, prev)?.0,
            };
            prev = unhex(&meta.tail_mac).or(prev);
            metas.push((name.clone(), meta));
        }
        let (tail, next_seq) = metas.last().map_or((ZERO, 1), |(_, m)| {
            (
                unhex(&m.tail_mac).unwrap_or(ZERO),
                m.last_seq.saturating_add(1),
            )
        });
        let mut store = Self {
            cfg,
            metas,
            file: None,
            tail,
            next_seq,
        };
        store.enforce_retention()?;
        Ok(store)
    }

    #[must_use]
    pub fn next_seq(&self) -> u64 {
        self.next_seq
    }

    fn write_idx(&self, name: &str, meta: &SegmentMeta) -> Result<(), CollaudoError> {
        let path = self.cfg.dir.join(name).with_extension("idx");
        let tmp = path.with_extension("tmp");
        fs::write(&tmp, serde_json::to_vec(meta)?)?;
        restrict(&tmp, false)?;
        fs::rename(&tmp, &path)?;
        Ok(())
    }

    fn rotate(&mut self) -> Result<(), CollaudoError> {
        if let Some((name, meta)) = self.metas.last() {
            self.write_idx(name, meta)?;
        }
        self.file = None;
        Ok(())
    }

    fn enforce_retention(&mut self) -> Result<(), CollaudoError> {
        while self.metas.len() > self.cfg.keep_segments.max(1) {
            let (name, _) = self.metas.remove(0);
            let path = self.cfg.dir.join(&name);
            let _ = fs::remove_file(path.with_extension("idx"));
            fs::remove_file(path)?;
        }
        Ok(())
    }

    fn writer(&mut self, seq: u64) -> Result<&mut File, CollaudoError> {
        let rotate = self.file.is_some()
            && self
                .metas
                .last()
                .is_some_and(|(_, m)| m.bytes >= self.cfg.segment_bytes);
        if rotate {
            self.rotate()?;
            self.enforce_retention()?;
        }
        if self.file.is_none() {
            let reuse = self
                .metas
                .last()
                .is_some_and(|(_, m)| m.bytes < self.cfg.segment_bytes);
            let name = if reuse {
                self.metas
                    .last()
                    .map_or_else(|| segment_name(seq), |(n, _)| n.clone())
            } else {
                segment_name(seq)
            };
            let path = self.cfg.dir.join(&name);
            let mut file = OpenOptions::new().create(true).append(true).open(&path)?;
            restrict(&path, false)?;
            if reuse && !ends_with_newline(&path) {
                file.write_all(b"\n")?;
            }
            if !reuse {
                let meta = SegmentMeta {
                    head_prev: Some(hex(&self.tail)),
                    ..SegmentMeta::default()
                };
                self.metas.push((name, meta));
                self.enforce_retention()?;
            }
            self.file = Some(file);
        }
        self.file.as_mut().ok_or(CollaudoError::Corrupt("writer"))
    }

    pub fn append(&mut self, env: &Envelope) -> Result<(), CollaudoError> {
        env.validate()?;
        let json = serde_json::to_string(env)?;
        let next = mac(&self.cfg.key, &self.tail, json.as_bytes());
        let line = format!("{}\t{}\n", hex(&next), json);
        let file = self.writer(env.seq)?;
        file.write_all(line.as_bytes())?;
        file.flush()?;
        self.tail = next;
        self.next_seq = env.seq.saturating_add(1);
        let bytes = u64::try_from(line.len()).unwrap_or(u64::MAX);
        if let Some((_, meta)) = self.metas.last_mut() {
            add_meta(meta, env, bytes, &next);
        }
        Ok(())
    }

    pub fn flush_index(&self) -> Result<(), CollaudoError> {
        match self.metas.last() {
            Some((name, meta)) => self.write_idx(name, meta),
            None => Ok(()),
        }
    }

    #[must_use]
    pub fn segments(&self) -> Vec<(String, SegmentMeta)> {
        self.metas.clone()
    }

    pub fn query(&self, q: &Query) -> Result<Vec<Envelope>, CollaudoError> {
        let limit = if q.limit == 0 { 500 } else { q.limit.min(5000) };
        let mut out = Vec::new();
        for (name, meta) in &self.metas {
            if meta.last_seq <= q.since_seq && meta.lines > 0 {
                continue;
            }
            if q.from_ms.is_some_and(|f| meta.max_ms < f)
                || q.to_ms.is_some_and(|t| meta.min_ms > t)
            {
                continue;
            }
            if let (Some(corr), true) = (&q.corr, meta.corrs_complete) {
                if !meta.corrs.contains(corr) {
                    continue;
                }
            }
            if let Some(domain) = q.domain {
                if !meta.counts.keys().any(|k| k.starts_with(domain.as_str())) {
                    continue;
                }
            }
            let reader = BufReader::new(File::open(self.cfg.dir.join(name))?);
            for line in reader.lines() {
                let line = line?;
                let Some((_, json)) = split_line(&line) else {
                    continue;
                };
                let Ok(env) = serde_json::from_str::<Envelope>(json) else {
                    continue;
                };
                if matches_query(&env, q) {
                    out.push(env);
                    if out.len() >= limit {
                        return Ok(out);
                    }
                }
            }
        }
        Ok(out)
    }

    pub fn verify(&self) -> Result<Integrity, CollaudoError> {
        let mut report = Integrity {
            segments: 0,
            lines: 0,
            ok: true,
            anchored: true,
            broken_segment: None,
        };
        let mut prev: Option<[u8; 32]> = None;
        for (i, (name, meta)) in self.metas.iter().enumerate() {
            let head = meta.head_prev.as_deref().and_then(unhex);
            if i == 0 && head.is_none() {
                report.anchored = false;
            }
            let anchor = if i == 0 { head } else { prev };
            if i > 0 && head.is_some() && head != prev {
                report.ok = false;
                report.broken_segment.get_or_insert_with(|| name.clone());
            }
            let (scanned, ok) = scan(&self.cfg.dir.join(name), &self.cfg.key, anchor)?;
            report.segments = report.segments.saturating_add(1);
            report.lines = report.lines.saturating_add(scanned.lines);
            if !ok {
                report.ok = false;
                report.broken_segment.get_or_insert_with(|| name.clone());
            }
            prev = unhex(&scanned.tail_mac).or(prev);
        }
        Ok(report)
    }
}

fn ends_with_newline(path: &Path) -> bool {
    use std::io::{Read, Seek, SeekFrom};
    let Ok(mut file) = File::open(path) else {
        return true;
    };
    let Ok(len) = file.metadata().map(|m| m.len()) else {
        return true;
    };
    if len == 0 || file.seek(SeekFrom::Start(len.saturating_sub(1))).is_err() {
        return true;
    }
    let mut last = [0u8; 1];
    file.read_exact(&mut last)
        .map_or(true, |()| last[0] == b'\n')
}

fn matches_query(env: &Envelope, q: &Query) -> bool {
    env.seq > q.since_seq
        && q.from_ms.is_none_or(|f| env.at_ms >= f)
        && q.to_ms.is_none_or(|t| env.at_ms <= t)
        && q.domain.is_none_or(|d| env.domain == d)
        && q.min_level.is_none_or(|l| env.level >= l)
        && q.corr.as_ref().is_none_or(|c| env.corr.as_ref() == Some(c))
        && q.kind_prefix
            .as_ref()
            .is_none_or(|p| env.kind.starts_with(p.as_str()))
}

#[cfg(unix)]
fn restrict(path: &Path, dir: bool) -> Result<(), CollaudoError> {
    use std::os::unix::fs::PermissionsExt;
    let mode = if dir { 0o700 } else { 0o600 };
    fs::set_permissions(path, fs::Permissions::from_mode(mode))?;
    Ok(())
}

#[cfg(not(unix))]
fn restrict(_path: &Path, _dir: bool) -> Result<(), CollaudoError> {
    Ok(())
}
