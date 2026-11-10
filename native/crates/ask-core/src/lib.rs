#![forbid(unsafe_code)]

pub mod error;
pub mod evidence;
pub mod format;
pub mod matcher;
pub mod parser;
pub mod query;

#[cfg(test)]
mod tests;

pub use error::AskError;
pub use evidence::{AskAnswer, EvidenceCitation, build_citations};
pub use format::format_answer;
pub use matcher::{ScoredMatch, match_sightings};
pub use parser::parse;
pub use query::{AskQuery, QueryLang, QuestionKind, RoleTarget};

use nuxiva_memory_core::Sighting;

#[must_use]
pub fn evaluate(query: &AskQuery, sightings: &[Sighting]) -> AskAnswer {
    let matches = match_sightings(query, sightings);
    let citations = build_citations(&matches, 5);
    let found = !citations.is_empty();
    let summary = format_answer(query, &citations);

    AskAnswer {
        found,
        summary,
        citations,
        scanned: sightings.len(),
        matched_count: matches.len(),
    }
}

pub fn ask(text: &str, now_ms: u64, sightings: &[Sighting]) -> Result<AskAnswer, AskError> {
    let query = parse(text, now_ms)?;
    Ok(evaluate(&query, sightings))
}
