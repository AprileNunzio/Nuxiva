use std::fs;
use std::path::PathBuf;

use nuxiva_mcp_core::glob_match;

use super::io::{Kind, date_text, kind_of, read_limited, size_text};
use super::paths::{Boundary, Fault, Need};

const NUL_PROBE: usize = 8_192;

pub struct ReadLimits {
    pub text: usize,
    pub list: usize,
    pub find: usize,
    pub entries: usize,
}

pub fn list_dir(b: &Boundary, limits: &ReadLimits, path: &str) -> Result<String, Fault> {
    let target = b.resolve(path, Need::Read)?;
    if kind_of(&target.path)? != Kind::Dir {
        return Err(Fault::NotDir);
    }
    let mut items: Vec<(bool, String, u64)> = Vec::new();
    for entry in fs::read_dir(&target.path).map_err(|_| Fault::Io)?.flatten() {
        let name = entry.file_name().to_string_lossy().into_owned();
        if !b.visible(&name) {
            continue;
        }
        match kind_of(&entry.path()) {
            Ok(Kind::Dir) => items.push((false, name, 0)),
            Ok(Kind::File(size)) => items.push((true, name, size)),
            _ => {}
        }
    }
    items.sort_by_key(|a| (a.0, a.1.to_lowercase()));
    let rows: Vec<String> = items
        .iter()
        .take(limits.list)
        .map(|(is_file, name, size)| {
            if *is_file {
                format!("📄 {name} ({})", size_text(*size))
            } else {
                format!("📁 {name}")
            }
        })
        .collect();
    let body = if rows.is_empty() {
        "(vuota)".to_owned()
    } else {
        rows.join("\n")
    };
    Ok(format!("{}:\n{body}", target.path.display()))
}

pub fn read_file(b: &Boundary, limits: &ReadLimits, path: &str) -> Result<String, Fault> {
    let target = b.resolve(path, Need::Read)?;
    b.check_extension(&target)?;
    let Kind::File(size) = kind_of(&target.path)? else {
        return Err(Fault::NotFile);
    };
    let max = b.config(&target)?.max_bytes;
    if size > max {
        return Err(Fault::TooBig);
    }
    let data = read_limited(&target.path, max)?;
    if data.iter().take(NUL_PROBE).any(|byte| *byte == 0) {
        return Err(Fault::Binary);
    }
    let text = String::from_utf8_lossy(&data);
    let total = text.chars().count();
    let mut out: String = text.chars().take(limits.text).collect();
    if total > limits.text {
        out.push_str("\n…(troncato)");
    }
    Ok(out)
}

pub fn file_info(b: &Boundary, path: &str) -> Result<String, Fault> {
    let target = b.resolve(path, Need::Read)?;
    let size = match kind_of(&target.path)? {
        Kind::File(size) => size,
        Kind::Dir => 0,
    };
    Ok(format!(
        "{}: {}, modificato il {}",
        target.path.display(),
        size_text(size),
        date_text(&target.path)
    ))
}

fn matcher(pattern: &str) -> impl Fn(&str) -> bool {
    let mut wanted = pattern.trim().to_lowercase();
    if wanted.is_empty() {
        "*".clone_into(&mut wanted);
    }
    if !wanted.contains('*') {
        wanted = format!("*{wanted}*");
    }
    move |name: &str| glob_match(&wanted, &name.to_lowercase())
}

pub fn find_files(
    b: &Boundary,
    limits: &ReadLimits,
    pattern: &str,
    root: &str,
) -> Result<String, Fault> {
    let base = b.resolve(root, Need::Read)?;
    if kind_of(&base.path)? != Kind::Dir {
        return Err(Fault::NotDir);
    }
    let max_depth = b.config(&base)?.max_depth;
    let hit = matcher(pattern);
    let mut found: Vec<String> = Vec::new();
    let mut stack: Vec<(PathBuf, usize)> = vec![(base.path.clone(), 0)];
    let mut visited = 0usize;
    'walk: while let Some((folder, depth)) = stack.pop() {
        let Ok(reader) = fs::read_dir(&folder) else {
            continue;
        };
        let mut names: Vec<(String, PathBuf)> = reader
            .flatten()
            .map(|e| (e.file_name().to_string_lossy().into_owned(), e.path()))
            .collect();
        names.sort();
        let mut subdirs = Vec::new();
        for (name, path) in names {
            visited = visited.saturating_add(1);
            if visited > limits.entries || found.len() >= limits.find {
                break 'walk;
            }
            if !b.visible(&name) {
                continue;
            }
            let Ok(kind) = kind_of(&path) else {
                continue;
            };
            if hit(&name) {
                found.push(path.display().to_string());
            }
            if kind == Kind::Dir && !name.starts_with('.') && depth < max_depth {
                subdirs.push((path, depth.saturating_add(1)));
            }
        }
        stack.extend(subdirs.into_iter().rev());
    }
    found.truncate(limits.find);
    if found.is_empty() {
        Ok(format!("nessun file trovato in {}", base.path.display()))
    } else {
        Ok(found.join("\n"))
    }
}
