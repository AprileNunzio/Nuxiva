use serde::Serialize;

const MAX_ENTRIES: usize = 200;
const MAX_SUMMARY: usize = 240;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ChangeEntry {
    pub sha: String,
    pub kind: &'static str,
    pub scope: Option<String>,
    pub breaking: bool,
    pub summary: String,
}

fn kind_of(raw: &str) -> &'static str {
    match raw.to_ascii_lowercase().as_str() {
        "feat" | "feature" => "feat",
        "fix" | "bugfix" | "hotfix" => "fix",
        "perf" => "perf",
        "refactor" => "refactor",
        "docs" | "doc" => "docs",
        "test" | "tests" => "test",
        "ci" | "build" => "build",
        "sec" | "security" => "security",
        "chore" | "style" => "chore",
        _ => "other",
    }
}

fn sanitize(text: &str, limit: usize) -> String {
    text.chars()
        .filter(|c| !c.is_control())
        .take(limit)
        .collect::<String>()
        .trim()
        .to_owned()
}

fn parse_subject(subject: &str) -> (&'static str, Option<String>, bool, String) {
    let primary = subject.split(" / ").next().unwrap_or(subject).trim();
    let Some((head, rest)) = primary.split_once(':') else {
        return ("other", None, false, sanitize(primary, MAX_SUMMARY));
    };
    let head = head.trim();
    let bang = head.ends_with('!');
    let head = head.trim_end_matches('!');
    let (kind_raw, scope) = match head.split_once('(') {
        Some((k, s)) => (
            k,
            s.strip_suffix(')')
                .map(|v| sanitize(v, 40))
                .filter(|v| !v.is_empty()),
        ),
        None => (head, None),
    };
    let well_formed = !kind_raw.is_empty() && kind_raw.chars().all(|c| c.is_ascii_alphabetic());
    if !well_formed {
        return ("other", None, false, sanitize(primary, MAX_SUMMARY));
    }
    let breaking = bang || rest.contains("BREAKING CHANGE");
    (
        kind_of(kind_raw),
        scope,
        breaking,
        sanitize(rest, MAX_SUMMARY),
    )
}

#[must_use]
pub fn parse_oneline(log: &str) -> Vec<ChangeEntry> {
    log.lines()
        .filter_map(|line| {
            let (sha, subject) = line.trim().split_once(' ')?;
            let valid = (7..=64).contains(&sha.len()) && sha.bytes().all(|b| b.is_ascii_hexdigit());
            if !valid {
                return None;
            }
            let (kind, scope, breaking, summary) = parse_subject(subject);
            Some(ChangeEntry {
                sha: sha.to_ascii_lowercase(),
                kind,
                scope,
                breaking,
                summary,
            })
        })
        .take(MAX_ENTRIES)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_conventional_commits() {
        let log = "3c24654 docs(readme): traduzioni / translations\nabc1234 feat(updater)!: nuova console\nzzz nope\n1234567 Merge branch main\n";
        let out = parse_oneline(log);
        assert_eq!(out.len(), 3);
        let first = out.first();
        assert_eq!(first.map(|e| e.kind), Some("docs"));
        assert_eq!(
            first.and_then(|e| e.scope.clone()).as_deref(),
            Some("readme")
        );
        assert_eq!(first.map(|e| e.summary.as_str()), Some("traduzioni"));
        assert_eq!(out.get(1).map(|e| e.breaking), Some(true));
        assert_eq!(out.get(2).map(|e| e.kind), Some("other"));
    }
}
