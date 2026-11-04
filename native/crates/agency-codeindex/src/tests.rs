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
    assert!(search(&tree.0, "  ", 10)?.is_empty());
    assert_eq!(search(&tree.0, "product", 1)?.len(), 1);
    Ok(())
}
