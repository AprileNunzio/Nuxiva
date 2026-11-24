use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write;

use capability_registry::{Role, tokenize};

use crate::doc::{Doc, parse};
use crate::error::{DossierError, DossierResult};

pub const REQUIRED: [&str; 7] = [
    "principio",
    "grafica",
    "sicurezza",
    "architettura",
    "dati",
    "test",
    "decisioni",
];
pub const MAX_SELECTION_TOKENS: usize = 1_500;

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct SectionRef {
    pub file: String,
    pub section: String,
}

impl SectionRef {
    #[must_use]
    pub fn cite(&self) -> String {
        format!("{}#{}", self.file, self.section)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Picked {
    pub reference: SectionRef,
    pub summary: String,
    pub body: String,
}

#[derive(Debug, Clone, Default)]
pub struct Dossier {
    docs: BTreeMap<String, Doc>,
    approved: Option<[u8; 32]>,
    log: Vec<String>,
}

fn tokens_of(text: &str) -> usize {
    text.len().div_ceil(4)
}

impl Dossier {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set(&mut self, name: &str, text: &str, reason: &str) -> DossierResult<Vec<SectionRef>> {
        let doc = parse(name, text)?;
        let before = self.docs.get(name).cloned();
        let changed: Vec<SectionRef> = doc
            .sections
            .iter()
            .filter(|s| {
                before.as_ref().is_none_or(|b| {
                    b.sections
                        .iter()
                        .find(|o| o.id == s.id)
                        .is_none_or(|o| o.body != s.body || o.summary != s.summary)
                })
            })
            .map(|s| SectionRef {
                file: name.to_owned(),
                section: s.id.clone(),
            })
            .collect();
        if before.is_some() {
            self.log.push(format!("revise {name}: {reason}"));
            self.approved = None;
        }
        self.docs.insert(name.to_owned(), doc);
        Ok(changed)
    }

    #[must_use]
    pub fn log(&self) -> &[String] {
        &self.log
    }

    #[must_use]
    pub fn digest(&self) -> [u8; 32] {
        let mut hasher = blake3::Hasher::new();
        for (name, doc) in &self.docs {
            hasher.update(name.as_bytes());
            hasher.update(&doc.hash);
        }
        *hasher.finalize().as_bytes()
    }

    pub fn complete(&self) -> DossierResult<()> {
        for name in REQUIRED {
            if !self.docs.contains_key(name) {
                return Err(DossierError::Missing(name.to_owned()));
            }
        }
        Ok(())
    }

    pub fn approve(&mut self, role: Role) -> DossierResult<()> {
        if !role.permits(Role::Family) {
            return Err(DossierError::RoleDenied);
        }
        self.complete()?;
        self.approved = Some(self.digest());
        Ok(())
    }

    pub fn ready(&self) -> DossierResult<()> {
        self.complete()?;
        if self.approved == Some(self.digest()) {
            Ok(())
        } else {
            Err(DossierError::NotApproved)
        }
    }

    #[must_use]
    pub fn select(&self, query: &str, budget_tokens: usize) -> Vec<Picked> {
        let terms: BTreeSet<String> = tokenize(query).into_iter().collect();
        let budget = budget_tokens.min(MAX_SELECTION_TOKENS);
        let mut scored: Vec<(usize, &str, &crate::doc::Section)> = Vec::new();
        for (name, doc) in &self.docs {
            for section in &doc.sections {
                let words: BTreeSet<String> = tokenize(&format!(
                    "{} {}",
                    section.id.replace('_', " "),
                    section.summary
                ))
                .into_iter()
                .collect();
                let score = terms.intersection(&words).count();
                if score > 0 {
                    scored.push((score, name.as_str(), section));
                }
            }
        }
        scored.sort_by(|a, b| {
            b.0.cmp(&a.0)
                .then_with(|| a.1.cmp(b.1))
                .then_with(|| a.2.id.cmp(&b.2.id))
        });
        let mut used = 0usize;
        let mut out = Vec::new();
        for (_, name, section) in scored {
            let cost = tokens_of(&section.summary).saturating_add(tokens_of(&section.body));
            if used.saturating_add(cost) > budget {
                continue;
            }
            used = used.saturating_add(cost);
            out.push(Picked {
                reference: SectionRef {
                    file: name.to_owned(),
                    section: section.id.clone(),
                },
                summary: section.summary.clone(),
                body: section.body.clone(),
            });
        }
        out
    }

    #[must_use]
    pub fn denied(&self) -> BTreeSet<String> {
        let Some(doc) = self.docs.get("sicurezza") else {
            return BTreeSet::new();
        };
        doc.sections
            .iter()
            .flat_map(|s| s.body.lines())
            .filter_map(|line| line.trim().strip_prefix("deny:"))
            .map(|id| id.trim().to_owned())
            .filter(|id| !id.is_empty())
            .collect()
    }

    #[must_use]
    pub fn restrict(&self, allowed: &BTreeSet<String>) -> BTreeSet<String> {
        let denied = self.denied();
        allowed.difference(&denied).cloned().collect()
    }

    #[must_use]
    pub fn invalidated(
        changed: &[SectionRef],
        used: &BTreeMap<String, Vec<SectionRef>>,
    ) -> Vec<String> {
        used.iter()
            .filter(|(_, refs)| refs.iter().any(|r| changed.contains(r)))
            .map(|(step, _)| step.clone())
            .collect()
    }
}

#[must_use]
pub fn skeleton(name: &str) -> Option<String> {
    let sections: &[(&str, &str)] = match name {
        "principio" => &[
            ("goal", "What the project must achieve"),
            ("audience", "Who it is for"),
            ("success", "How success is measured"),
        ],
        "grafica" => &[
            ("style", "Visual language and tone"),
            ("layout", "Responsive layout rules"),
            ("assets", "Images, icons and fonts"),
        ],
        "sicurezza" => &[
            ("threats", "Main risks and abuse cases"),
            ("data", "Sensitive data and its protection"),
            ("limits", "Capabilities that are forbidden"),
        ],
        "architettura" => &[
            ("modules", "Modules and their boundaries"),
            ("flows", "Main data flows"),
            ("integrations", "External services and tools"),
        ],
        "dati" => &[
            ("entities", "Entities and their fields"),
            ("retention", "How long data is kept"),
        ],
        "test" => &[
            ("acceptance", "Measurable acceptance criteria"),
            ("cases", "Test cases and edge cases"),
        ],
        "decisioni" => &[("log", "Dated decisions with their reason")],
        _ => return None,
    };
    let mut out = format!("# {name}\n");
    for (id, summary) in sections {
        let _ = write!(out, "\n## {id} - {summary}\nTo be written.\n");
    }
    Some(out)
}
