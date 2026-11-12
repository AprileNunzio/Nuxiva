use std::fs;
use std::path::PathBuf;

use crate::{Limits, ScanError, scan, search};

struct Tree(PathBuf);

impl Tree {
    fn new(tag: &str) -> Result<Self, ScanError> {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).map_err(|e| std::io::Error::other(e.to_string()))?;
        let root =
            std::env::temp_dir().join(format!("nxc-{tag}-{:016x}", u64::from_le_bytes(nonce)));
        fs::create_dir_all(root.join("src/api"))?;
        fs::create_dir_all(root.join("node_modules/lib"))?;
        fs::create_dir_all(root.join(".git"))?;
        fs::write(
            root.join("src/api/catalog.py"),
            "def list_products(db):\n    return db.products()\n",
        )?;
        fs::write(
            root.join("src/cart.js"),
            "export function addToCart(product) {}\n",
        )?;
        fs::write(root.join("node_modules/lib/products.js"), "products")?;
        fs::write(root.join(".git/config"), "products")?;
        fs::write(root.join("logo.bin"), [0u8, 1, 2, b'p'])?;
        Ok(Self(root))
    }
}

impl Drop for Tree {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn scan_skips_hidden_and_vendor_folders() -> Result<(), ScanError> {
    let tree = Tree::new("scan")?;
    let files: Vec<String> = scan(&tree.0, Limits::default())?
        .into_iter()
        .map(|f| f.path)
        .collect();
    assert_eq!(files, ["logo.bin", "src/api/catalog.py", "src/cart.js"]);
    Ok(())
}

#[test]
fn scan_respects_limits() -> Result<(), ScanError> {
    let tree = Tree::new("limits")?;
    let limits = Limits {
        max_files: 1,
        ..Limits::default()
    };
    assert_eq!(scan(&tree.0, limits)?.len(), 1);
    let shallow = Limits {
        max_depth: 0,
        ..Limits::default()
    };
    assert_eq!(scan(&tree.0, shallow)?.len(), 1);
    Ok(())
}

#[cfg(unix)]
#[test]
fn scan_does_not_follow_symlinks() -> Result<(), ScanError> {
    let tree = Tree::new("link")?;
    std::os::unix::fs::symlink("/etc", tree.0.join("src/etc"))?;
    let files = scan(&tree.0, Limits::default())?;
    assert!(files.iter().all(|f| !f.path.starts_with("src/etc")));
    assert!(scan(&tree.0.join("src/etc"), Limits::default()).is_err());
    Ok(())
}

#[test]
fn search_ranks_lines_and_ignores_binaries() -> Result<(), ScanError> {
    let tree = Tree::new("search")?;
    let hits = search(&tree.0, "products catalog", 10)?;
    assert_eq!(
        hits.first().map(|h| (h.path.as_str(), h.line)),
        Some(("src/api/catalog.py", 1))
    );
    assert!(hits.iter().all(|h| h.path != "logo.bin"));
    assert_eq!(search(&tree.0, "  ", 10)?, [] as [crate::search::Hit; 0]);
    let ranked = search(&tree.0, "product", 10)?;
    assert!(ranked.len() > 1);
    assert_eq!(
        Some(search(&tree.0, "product", 1)?.as_slice()),
        ranked.get(..1)
    );
    Ok(())
}

#[test]
fn incremental_sync_detects_changes_and_removals() -> Result<(), ScanError> {
    let tree = Tree::new("incremental")?;
    let mut index = crate::CodeIndex::new(10_000, 50 * 1024 * 1024);

    let s1 = index.sync_incremental(&tree.0, Limits::default())?;
    assert_eq!(s1.added, 3);
    assert_eq!(s1.updated, 0);

    let s2 = index.sync_incremental(&tree.0, Limits::default())?;
    assert_eq!(s2.added, 0);
    assert_eq!(s2.unchanged, 3);

    fs::write(
        tree.0.join("src/cart.js"),
        "export function addToCart(product) { /* modified */ }\n",
    )?;
    let s3 = index.sync_incremental(&tree.0, Limits::default())?;
    assert_eq!(s3.updated, 1);

    fs::remove_file(tree.0.join("src/cart.js"))?;
    let s4 = index.sync_incremental(&tree.0, Limits::default())?;
    assert_eq!(s4.removed, 1);
    assert_eq!(index.file_count(), 2);
    Ok(())
}

#[test]
fn million_file_corpus_performance_measurement() {
    let metrics = crate::CodeIndex::measure_corpus(1_000_000);
    assert_eq!(metrics.file_count, 1_000_000);
    assert!(metrics.memory_bytes < 350 * 1024 * 1024);
    assert!(metrics.search_latency_micros < 100_000);
    assert!(metrics.update_latency_micros > 0);
}

#[test]
fn extract_outline_and_search_symbols_across_languages() -> Result<(), ScanError> {
    let tree = Tree::new("symbols")?;
    let outline = crate::outline_file(&tree.0, "src/api/catalog.py")?;
    assert_eq!(outline.language, "python");
    assert_eq!(outline.symbols.len(), 1);
    assert_eq!(
        outline.symbols.first().map(|s| s.name.as_str()),
        Some("list_products")
    );

    let sym_hits = crate::search_symbols(&tree.0, "addToCart", 10)?;
    assert_eq!(sym_hits.len(), 1);
    assert_eq!(
        sym_hits.first().map(|h| h.path.as_str()),
        Some("src/cart.js")
    );
    Ok(())
}
