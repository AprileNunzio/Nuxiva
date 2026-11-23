use std::fs;
use std::path::PathBuf;

use super::{BenchConfig, BenchError, body, relative_path, run};

fn config() -> BenchConfig {
    BenchConfig {
        files: 300,
        files_per_dir: 25,
        seed: 7,
        max_memory_bytes: 64 * 1024 * 1024,
        search_queries: vec!["query_target_42".to_owned(), "pub".to_owned()],
        search_limit: 10,
        search_rounds: 5,
        updated_files: 20,
        added_files: 15,
        removed_files: 10,
    }
}

struct Root(PathBuf);

impl Root {
    fn new(tag: &str) -> Result<Self, BenchError> {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).map_err(|e| std::io::Error::other(e.to_string()))?;
        Ok(Self(std::env::temp_dir().join(format!(
            "nxb-{tag}-{:016x}",
            u64::from_le_bytes(nonce)
        ))))
    }
}

impl Drop for Root {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn run_is_consistent_on_real_files() -> Result<(), BenchError> {
    let root = Root::new("run")?;
    let report = run(&root.0, &config())?;
    assert_eq!(report.indexed_files, 300);
    assert!(report.incremental.consistent);
    assert_eq!(report.incremental.indexed_files, 305);
    assert_eq!(report.noop_sync.stats.added, 0);
    assert_eq!(report.noop_sync.stats.updated, 0);
    assert_eq!(report.noop_sync.stats.removed, 0);
    assert_eq!(report.search.len(), 2);
    assert!(report.search.iter().all(|q| q.hits > 0));
    Ok(())
}

#[test]
fn corpus_is_deterministic() {
    let cfg = config();
    assert_eq!(body(&cfg, 5, 0), body(&cfg, 5, 0));
    assert_ne!(body(&cfg, 5, 0), body(&cfg, 5, 1));
    assert_eq!(relative_path(&cfg, 0), "pkg0000/mod0000/item00000000.rs");
    assert_eq!(relative_path(&cfg, 26), "pkg0000/mod0001/item00000026.rs");
}

#[test]
fn rejects_invalid_configuration() {
    let mut cfg = config();
    cfg.updated_files = 295;
    cfg.removed_files = 10;
    assert!(cfg.validate().is_err());
    assert!(BenchConfig::from_json("{\"files\":1,\"extra\":2}").is_err());
    cfg = config();
    cfg.search_queries.clear();
    assert!(cfg.validate().is_err());
}

#[test]
fn refuses_non_empty_root() -> Result<(), BenchError> {
    let root = Root::new("busy")?;
    fs::create_dir_all(&root.0)?;
    fs::write(root.0.join("keep.txt"), "x")?;
    assert!(matches!(
        run(&root.0, &config()),
        Err(BenchError::RootNotEmpty)
    ));
    Ok(())
}
