use crate::error::{DossierError, DossierResult};

pub const MAX_FILE_BYTES: usize = 128 * 1024;
pub const MAX_SECTIONS: usize = 64;
pub const MAX_SUMMARY_BYTES: usize = 160;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Section {
    pub id: String,
    pub summary: String,
    pub body: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Doc {
    pub name: String,
    pub sections: Vec<Section>,
    pub hash: [u8; 32],
}

pub fn slug(text: &str, max: usize) -> bool {
    !text.is_empty()
        && text.len() <= max
        && text
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

pub fn parse(name: &str, text: &str) -> DossierResult<Doc> {
    if !slug(name, 32) || text.len() > MAX_FILE_BYTES {
        return Err(DossierError::Invalid("file"));
    }
    if text
        .chars()
        .any(|c| c.is_control() && c != '\n' && c != '\t')
    {
        return Err(DossierError::Invalid("control"));
    }
    let mut sections: Vec<Section> = Vec::new();
    for line in text.lines() {
        if let Some(head) = line.strip_prefix("## ") {
            let (id, summary) = head
                .split_once(" - ")
                .ok_or(DossierError::Invalid("heading"))?;
            if !slug(id.trim(), 48)
                || summary.trim().is_empty()
                || summary.len() > MAX_SUMMARY_BYTES
                || sections.iter().any(|s| s.id == id.trim())
            {
                return Err(DossierError::Invalid("heading"));
            }
            sections.push(Section {
                id: id.trim().to_owned(),
                summary: summary.trim().to_owned(),
                body: String::new(),
            });
        } else if let Some(last) = sections.last_mut() {
            last.body.push_str(line);
            last.body.push('\n');
        } else if !line.trim().is_empty() && !line.starts_with("# ") {
            return Err(DossierError::Invalid("preamble"));
        }
    }
    if sections.is_empty() || sections.len() > MAX_SECTIONS {
        return Err(DossierError::Invalid("sections"));
    }
    Ok(Doc {
        name: name.to_owned(),
        sections,
        hash: *blake3::hash(text.as_bytes()).as_bytes(),
    })
}
