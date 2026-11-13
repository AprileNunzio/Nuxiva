use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use super::io::{Kind, exists, kind_of, open_write, size_text, stamp};
use super::paths::{Boundary, Fault, Need, Target};

pub struct Budget {
    pub entries: usize,
}

fn unique(dir: &Path, name: &str) -> PathBuf {
    let first = dir.join(name);
    if !exists(&first) {
        return first;
    }
    (1u32..10_000)
        .map(|n| dir.join(format!("{n}-{name}")))
        .find(|p| !exists(p))
        .unwrap_or(first)
}

fn copy_tree(
    src: &Path,
    dst: &Path,
    depth: usize,
    max_depth: usize,
    budget: &mut usize,
) -> Result<(), Fault> {
    if depth > max_depth {
        return Err(Fault::Depth);
    }
    *budget = budget.checked_sub(1).ok_or(Fault::Limit)?;
    match kind_of(src)? {
        Kind::File(_) => fs::copy(src, dst).map(|_| ()).map_err(|_| Fault::Io),
        Kind::Dir => {
            fs::create_dir_all(dst).map_err(|_| Fault::Io)?;
            for entry in fs::read_dir(src).map_err(|_| Fault::Io)?.flatten() {
                copy_tree(
                    &entry.path(),
                    &dst.join(entry.file_name()),
                    depth.saturating_add(1),
                    max_depth,
                    budget,
                )?;
            }
            Ok(())
        }
    }
}

fn relocate(src: &Path, dst: &Path, budget: &mut usize) -> Result<(), Fault> {
    match fs::rename(src, dst) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::CrossesDevices => {
            copy_tree(src, dst, 0, usize::MAX, budget)?;
            let removed = match kind_of(src)? {
                Kind::Dir => fs::remove_dir_all(src),
                Kind::File(_) => fs::remove_file(src),
            };
            removed.map_err(|_| Fault::Io)
        }
        Err(_) => Err(Fault::Io),
    }
}

fn to_trash(b: &Boundary, path: &Path, budget: &mut usize) -> Result<PathBuf, Fault> {
    let trash = b.trash.as_ref().ok_or(Fault::NoTrash)?;
    let folder = trash.join(stamp());
    fs::create_dir_all(&folder).map_err(|_| Fault::Io)?;
    let name = path.file_name().ok_or(Fault::Invalid)?.to_string_lossy();
    let dest = unique(&folder, &name);
    relocate(path, &dest, budget)?;
    Ok(dest)
}

fn ensure_parent(target: &Target) -> Result<(), Fault> {
    let parent = target.path.parent().ok_or(Fault::Invalid)?;
    fs::create_dir_all(parent).map_err(|_| Fault::Io)
}

pub fn write_file(
    b: &Boundary,
    budget: &mut Budget,
    path: &str,
    content: &str,
    append: bool,
) -> Result<String, Fault> {
    let target = b.resolve(path, Need::Write)?;
    b.check_extension(&target)?;
    if Boundary::is_root(&target) {
        return Err(Fault::IsRoot);
    }
    let max = b.config(&target)?.max_bytes;
    if u64::try_from(content.len()).unwrap_or(u64::MAX) > max {
        return Err(Fault::TooBig);
    }
    ensure_parent(&target)?;
    match kind_of(&target.path) {
        Ok(Kind::Dir) => return Err(Fault::NotFile),
        Ok(Kind::File(size)) => {
            if append && size.saturating_add(u64::try_from(content.len()).unwrap_or(u64::MAX)) > max
            {
                return Err(Fault::TooBig);
            }
            if !append {
                to_trash_copy(b, &target.path, &mut budget.entries)?;
            }
        }
        Err(Fault::Missing) => {}
        Err(other) => return Err(other),
    }
    let mut file = open_write(&target.path, append).map_err(|_| Fault::Io)?;
    file.write_all(content.as_bytes()).map_err(|_| Fault::Io)?;
    file.flush().map_err(|_| Fault::Io)?;
    let size = match kind_of(&target.path)? {
        Kind::File(size) => size,
        Kind::Dir => 0,
    };
    Ok(format!(
        "scritto {} ({})",
        target.path.display(),
        size_text(size)
    ))
}

fn to_trash_copy(b: &Boundary, path: &Path, budget: &mut usize) -> Result<PathBuf, Fault> {
    let trash = b.trash.as_ref().ok_or(Fault::NoTrash)?;
    let folder = trash.join(stamp());
    fs::create_dir_all(&folder).map_err(|_| Fault::Io)?;
    let name = path.file_name().ok_or(Fault::Invalid)?.to_string_lossy();
    let dest = unique(&folder, &name);
    *budget = budget.checked_sub(1).ok_or(Fault::Limit)?;
    fs::copy(path, &dest).map_err(|_| Fault::Io)?;
    Ok(dest)
}

pub fn make_dir(b: &Boundary, path: &str) -> Result<String, Fault> {
    let target = b.resolve(path, Need::Write)?;
    fs::create_dir_all(&target.path).map_err(|_| Fault::Io)?;
    Ok(format!("cartella pronta: {}", target.path.display()))
}

fn destination(b: &Boundary, src: &Target, dst: &str) -> Result<Target, Fault> {
    let first = b.resolve(dst, Need::Write)?;
    if matches!(kind_of(&first.path), Ok(Kind::Dir)) {
        let name = src
            .path
            .file_name()
            .ok_or(Fault::Invalid)?
            .to_string_lossy();
        let joined = first.path.join(name.as_ref());
        return b.resolve(&joined.to_string_lossy(), Need::Write);
    }
    Ok(first)
}

pub fn copy(b: &Boundary, budget: &mut Budget, src: &str, dst: &str) -> Result<String, Fault> {
    let from = b.resolve(src, Need::Read)?;
    let to = destination(b, &from, dst)?;
    b.check_extension(&to)?;
    if to.path.starts_with(&from.path) {
        return Err(Fault::Invalid);
    }
    kind_of(&from.path)?;
    ensure_parent(&to)?;
    let max_depth = b.config(&from)?.max_depth;
    copy_tree(&from.path, &to.path, 0, max_depth, &mut budget.entries)?;
    Ok(format!("copiato in {}", to.path.display()))
}

pub fn move_path(b: &Boundary, budget: &mut Budget, src: &str, dst: &str) -> Result<String, Fault> {
    let from = b.resolve(src, Need::Write)?;
    if Boundary::is_root(&from) {
        return Err(Fault::IsRoot);
    }
    let to = destination(b, &from, dst)?;
    b.check_extension(&to)?;
    if to.path.starts_with(&from.path) {
        return Err(Fault::Invalid);
    }
    kind_of(&from.path)?;
    ensure_parent(&to)?;
    if exists(&to.path) {
        to_trash(b, &to.path, &mut budget.entries)?;
    }
    relocate(&from.path, &to.path, &mut budget.entries)?;
    Ok(format!("spostato in {}", to.path.display()))
}

pub fn delete(b: &Boundary, budget: &mut Budget, path: &str) -> Result<String, Fault> {
    let target = b.resolve(path, Need::Write)?;
    if Boundary::is_root(&target) {
        return Err(Fault::IsRoot);
    }
    kind_of(&target.path)?;
    let dest = to_trash(b, &target.path, &mut budget.entries)?;
    Ok(format!("spostato nel cestino: {}", dest.display()))
}
