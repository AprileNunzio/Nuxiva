use std::fs;
use std::io::Read;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::scan::{Limits, ScanError, language, scan};

const MAX_SIGNATURE_CHARS: usize = 200;
const MAX_SYMBOLS_PER_FILE: usize = 256;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SymbolKind {
    Function,
    Struct,
    Class,
    Enum,
    Trait,
    Interface,
    Module,
    Constant,
    Table,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CodeSymbol {
    pub name: String,
    pub kind: SymbolKind,
    pub start_line: usize,
    pub end_line: usize,
    pub signature: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileOutline {
    pub path: String,
    pub language: &'static str,
    pub total_lines: usize,
    pub symbols: Vec<CodeSymbol>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SymbolHit {
    pub path: String,
    pub symbol: CodeSymbol,
}

fn clean_ident(raw: &str) -> String {
    raw.chars()
        .take_while(|c| c.is_alphanumeric() || *c == '_')
        .collect()
}

fn extract_after_keyword(trimmed: &str, keyword: &str) -> Option<String> {
    let rest = trimmed.strip_prefix(keyword)?.trim_start();
    let ident = clean_ident(rest);
    if ident.is_empty() { None } else { Some(ident) }
}

fn classify_rust(trimmed: &str) -> Option<(SymbolKind, String)> {
    let stripped = trimmed
        .strip_prefix("pub(crate) ")
        .or_else(|| trimmed.strip_prefix("pub(super) "))
        .or_else(|| trimmed.strip_prefix("pub "))
        .unwrap_or(trimmed)
        .trim_start();
    let stripped = stripped
        .strip_prefix("async ")
        .unwrap_or(stripped)
        .trim_start();
    let stripped = stripped
        .strip_prefix("const ")
        .unwrap_or(stripped)
        .trim_start();

    if let Some(name) = extract_after_keyword(stripped, "fn ") {
        return Some((SymbolKind::Function, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "struct ") {
        return Some((SymbolKind::Struct, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "enum ") {
        return Some((SymbolKind::Enum, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "trait ") {
        return Some((SymbolKind::Trait, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "mod ") {
        return Some((SymbolKind::Module, name));
    }
    None
}

fn classify_python(trimmed: &str) -> Option<(SymbolKind, String)> {
    let stripped = trimmed
        .strip_prefix("async ")
        .unwrap_or(trimmed)
        .trim_start();
    if let Some(name) = extract_after_keyword(stripped, "def ") {
        return Some((SymbolKind::Function, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "class ") {
        return Some((SymbolKind::Class, name));
    }
    None
}

fn classify_js_ts(trimmed: &str) -> Option<(SymbolKind, String)> {
    let stripped = trimmed
        .strip_prefix("export ")
        .unwrap_or(trimmed)
        .trim_start();
    let stripped = stripped
        .strip_prefix("default ")
        .unwrap_or(stripped)
        .trim_start();
    let stripped = stripped
        .strip_prefix("async ")
        .unwrap_or(stripped)
        .trim_start();

    if let Some(name) = extract_after_keyword(stripped, "function ") {
        return Some((SymbolKind::Function, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "class ") {
        return Some((SymbolKind::Class, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "interface ") {
        return Some((SymbolKind::Interface, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "type ") {
        return Some((SymbolKind::Struct, name));
    }
    if let Some(name) = extract_after_keyword(stripped, "const ") {
        return Some((SymbolKind::Constant, name));
    }
    None
}

fn classify_sql(trimmed: &str) -> Option<(SymbolKind, String)> {
    let upper = trimmed.to_uppercase();
    if upper.starts_with("CREATE TABLE ") {
        let rest = trimmed.get(13..)?.trim_start();
        let rest = if rest.to_uppercase().starts_with("IF NOT EXISTS ") {
            rest.get(14..)?.trim_start()
        } else {
            rest
        };
        let name = clean_ident(rest);
        if !name.is_empty() {
            return Some((SymbolKind::Table, name));
        }
    }
    None
}

fn classify_line(lang: &str, line: &str) -> Option<(SymbolKind, String)> {
    let trimmed = line.trim_start();
    match lang {
        "rust" => classify_rust(trimmed),
        "python" => classify_python(trimmed),
        "javascript" | "typescript" => classify_js_ts(trimmed),
        "sql" => classify_sql(trimmed),
        _ => classify_rust(trimmed)
            .or_else(|| classify_python(trimmed))
            .or_else(|| classify_js_ts(trimmed)),
    }
}

#[must_use]
pub fn extract_outline(path: &str, content: &str) -> FileOutline {
    let lang = language(Path::new(path));
    let lines: Vec<&str> = content.lines().collect();
    let total_lines = lines.len();
    let mut symbols: Vec<CodeSymbol> = Vec::new();

    for (idx, &line) in lines.iter().enumerate() {
        if symbols.len() >= MAX_SYMBOLS_PER_FILE {
            break;
        }
        let line_no = idx.saturating_add(1);
        if let Some((kind, name)) = classify_line(lang, line) {
            if let Some(prev) = symbols.last_mut() {
                if prev.end_line == total_lines {
                    prev.end_line = idx.max(prev.start_line);
                }
            }
            let signature: String = line.trim().chars().take(MAX_SIGNATURE_CHARS).collect();
            symbols.push(CodeSymbol {
                name,
                kind,
                start_line: line_no,
                end_line: total_lines.max(line_no),
                signature,
            });
        }
    }

    FileOutline {
        path: path.to_owned(),
        language: lang,
        total_lines,
        symbols,
    }
}

pub fn outline_file(root: &Path, relative_path: &str) -> Result<FileOutline, ScanError> {
    if relative_path.is_empty()
        || relative_path.contains("..")
        || relative_path.starts_with('/')
        || relative_path.starts_with('\\')
    {
        return Err(ScanError::Io(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "invalid relative path",
        )));
    }
    let full = root.join(relative_path);
    let meta = fs::symlink_metadata(&full)?;
    if meta.file_type().is_symlink() || !meta.is_file() {
        return Err(ScanError::Io(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "target is not a regular file",
        )));
    }
    let file = fs::File::open(full)?;
    let mut bytes = Vec::new();
    let max = Limits::default().max_file_bytes;
    file.take(max.saturating_add(1)).read_to_end(&mut bytes)?;
    let content = String::from_utf8_lossy(&bytes);
    Ok(extract_outline(relative_path, &content))
}

pub fn search_symbols(root: &Path, query: &str, limit: usize) -> Result<Vec<SymbolHit>, ScanError> {
    let q = query.trim().to_lowercase();
    if q.is_empty() || limit == 0 {
        return Ok(Vec::new());
    }
    let mut hits = Vec::new();
    for entry in scan(root, Limits::default())? {
        if hits.len() >= limit {
            break;
        }
        let Ok(outline) = outline_file(root, &entry.path) else {
            continue;
        };
        for sym in outline.symbols {
            if sym.name.to_lowercase().contains(&q) {
                hits.push(SymbolHit {
                    path: entry.path.clone(),
                    symbol: sym,
                });
                if hits.len() >= limit {
                    break;
                }
            }
        }
    }
    Ok(hits)
}
