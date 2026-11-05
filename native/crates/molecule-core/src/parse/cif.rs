use super::{Lines, clip, coordinate};
use crate::element;
use crate::error::{MolError, MolResult};
use crate::model::{Atom, SecondaryKind, SecondaryRange, Structure};

const MAX_COLUMNS: usize = 256;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Category {
    Atoms,
    Helices,
    Sheets,
    Other,
}

fn category(tag: &str) -> Category {
    match tag.split_once('.').map(|(c, _)| c) {
        Some("_atom_site") => Category::Atoms,
        Some("_struct_conf") => Category::Helices,
        Some("_struct_sheet_range") => Category::Sheets,
        _ => Category::Other,
    }
}

fn tokens(line: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut chars = line.char_indices().peekable();
    while let Some(&(start, c)) = chars.peek() {
        if c.is_whitespace() {
            chars.next();
            continue;
        }
        if c == '#' {
            break;
        }
        if c == '\'' || c == '"' {
            chars.next();
            let mut value = String::new();
            while let Some((_, d)) = chars.next() {
                if d == c && chars.peek().is_none_or(|&(_, n)| n.is_whitespace()) {
                    break;
                }
                value.push(d);
            }
            out.push(value);
            continue;
        }
        let mut end = start;
        while let Some(&(i, d)) = chars.peek() {
            if d.is_whitespace() {
                break;
            }
            end = i.saturating_add(d.len_utf8());
            chars.next();
        }
        out.push(line.get(start..end).unwrap_or("").to_owned());
    }
    out
}

struct Loop {
    kind: Category,
    columns: Vec<String>,
    row: Vec<String>,
    in_header: bool,
}

impl Loop {
    fn column(&self, names: &[&str]) -> Option<usize> {
        names
            .iter()
            .find_map(|n| self.columns.iter().position(|c| c == n))
    }

    fn value<'a>(&self, row: &'a [String], names: &[&str]) -> Option<&'a str> {
        self.column(names)
            .and_then(|i| row.get(i))
            .map(String::as_str)
            .filter(|v| *v != "." && *v != "?")
    }
}

fn number(raw: Option<&str>, line: u32) -> MolResult<i32> {
    raw.ok_or(MolError::MissingColumn)?
        .trim()
        .parse()
        .map_err(|_| MolError::BadNumber(line))
}

fn atom(table: &Loop, row: &[String], line: u32) -> MolResult<Option<Atom>> {
    if table
        .value(row, &["_atom_site.pdbx_PDB_model_num"])
        .is_some_and(|m| m != "1")
    {
        return Ok(None);
    }
    if table
        .value(row, &["_atom_site.label_alt_id"])
        .is_some_and(|a| a != "A")
    {
        return Ok(None);
    }
    let name = clip(
        table
            .value(
                row,
                &["_atom_site.auth_atom_id", "_atom_site.label_atom_id"],
            )
            .unwrap_or(""),
        4,
    );
    let found = match table.value(row, &["_atom_site.type_symbol"]) {
        Some(symbol) => element::by_symbol(symbol),
        None => element::from_atom_name(&name),
    };
    let axis = |tag: &str| {
        coordinate(
            table.value(row, &[tag]).ok_or(MolError::MissingColumn)?,
            line,
        )
    };
    Ok(Some(Atom {
        residue: clip(
            table
                .value(
                    row,
                    &["_atom_site.auth_comp_id", "_atom_site.label_comp_id"],
                )
                .unwrap_or(""),
            3,
        ),
        chain: clip(
            table
                .value(
                    row,
                    &["_atom_site.auth_asym_id", "_atom_site.label_asym_id"],
                )
                .unwrap_or(""),
            4,
        ),
        seq: number(
            table.value(row, &["_atom_site.auth_seq_id", "_atom_site.label_seq_id"]),
            line,
        )
        .unwrap_or(0),
        position: [
            axis("_atom_site.Cartn_x")?,
            axis("_atom_site.Cartn_y")?,
            axis("_atom_site.Cartn_z")?,
        ],
        b_factor: table
            .value(row, &["_atom_site.B_iso_or_equiv"])
            .and_then(|v| v.parse().ok())
            .filter(|v: &f32| v.is_finite())
            .unwrap_or(0.0),
        element: found.number,
        hetero: table.value(row, &["_atom_site.group_PDB"]) == Some("HETATM"),
        name,
    }))
}

fn range(
    table: &Loop,
    row: &[String],
    line: u32,
    kind: SecondaryKind,
) -> MolResult<Option<SecondaryRange>> {
    let prefix = if kind == SecondaryKind::Helix {
        "_struct_conf"
    } else {
        "_struct_sheet_range"
    };
    if kind == SecondaryKind::Helix
        && !table
            .value(row, &["_struct_conf.conf_type_id"])
            .is_some_and(|t| t.starts_with("HELX"))
    {
        return Ok(None);
    }
    let tag = |field: &str| format!("{prefix}.{field}");
    let chain = table
        .value(row, &[&tag("beg_auth_asym_id"), &tag("beg_label_asym_id")])
        .unwrap_or("");
    let start = number(
        table.value(row, &[&tag("beg_auth_seq_id"), &tag("beg_label_seq_id")]),
        line,
    )?;
    let end = number(
        table.value(row, &[&tag("end_auth_seq_id"), &tag("end_label_seq_id")]),
        line,
    )?;
    Ok(Some(SecondaryRange {
        kind,
        chain: clip(chain, 4),
        start: start.min(end),
        end: start.max(end),
    }))
}

fn flush(
    table: &mut Loop,
    structure: &mut Structure,
    line: u32,
    max_atoms: usize,
) -> MolResult<()> {
    if table.columns.is_empty() || table.row.len() < table.columns.len() {
        return Ok(());
    }
    let row = std::mem::take(&mut table.row);
    match table.kind {
        Category::Atoms => {
            if let Some(atom) = atom(table, &row, line)? {
                if structure.atoms.len() >= max_atoms {
                    return Err(MolError::TooManyAtoms);
                }
                structure.atoms.push(atom);
            }
        }
        Category::Helices | Category::Sheets => {
            let kind = if table.kind == Category::Helices {
                SecondaryKind::Helix
            } else {
                SecondaryKind::Sheet
            };
            if structure.secondary.len() >= 100_000 {
                return Err(MolError::TooManyAtoms);
            }
            if let Some(found) = range(table, &row, line, kind)? {
                structure.secondary.push(found);
            }
        }
        Category::Other => {}
    }
    Ok(())
}

pub(super) fn parse(lines: Lines<'_>, max_atoms: usize) -> MolResult<Structure> {
    let mut structure = Structure::default();
    let mut table: Option<Loop> = None;
    let mut text: Option<String> = None;
    let mut pending_title = false;
    for entry in lines {
        let (number, line) = entry?;
        if let Some(buffer) = text.as_mut() {
            if line.starts_with(';') {
                let value = std::mem::take(buffer);
                text = None;
                if pending_title {
                    structure.title = clip(&value, 160);
                    pending_title = false;
                } else if let Some(t) = table.as_mut().filter(|t| !t.in_header) {
                    t.row.push(value);
                    flush(t, &mut structure, number, max_atoms)?;
                }
            } else if buffer.len() < 4096 {
                buffer.push_str(line.trim());
                buffer.push(' ');
            }
            continue;
        }
        if let Some(rest) = line.strip_prefix(';') {
            text = Some(format!("{} ", rest.trim()));
            continue;
        }
        let words = tokens(line);
        let Some(first) = words.first() else { continue };
        if first == "loop_" {
            table = Some(Loop {
                kind: Category::Other,
                columns: Vec::new(),
                row: Vec::new(),
                in_header: true,
            });
            continue;
        }
        if first.starts_with("data_") {
            if !structure.atoms.is_empty() {
                break;
            }
            table = None;
            continue;
        }
        if first.starts_with('_') {
            if let Some(t) = table.as_mut().filter(|t| t.in_header) {
                if t.columns.is_empty() {
                    t.kind = category(first);
                }
                if t.columns.len() >= MAX_COLUMNS {
                    return Err(MolError::MissingColumn);
                }
                t.columns.push(first.clone());
            } else {
                table = None;
                if first == "_struct.title" {
                    match words.get(1) {
                        Some(value) => structure.title = clip(value, 160),
                        None => pending_title = true,
                    }
                }
            }
            continue;
        }
        if pending_title {
            structure.title = clip(first, 160);
            pending_title = false;
            continue;
        }
        if let Some(t) = table.as_mut() {
            t.in_header = false;
            for word in words {
                t.row.push(word);
                flush(t, &mut structure, number, max_atoms)?;
            }
        }
    }
    Ok(structure)
}
