use serde::{Deserialize, Serialize};

const MAX_LINE: usize = 220;
const MAX_PACKAGE: usize = 100;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AptKind {
    Fetch,
    Read,
    Summary,
    Unpack,
    Setup,
    Trigger,
    Warn,
    Error,
    Other,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct AptSummary {
    pub upgraded: u32,
    pub installed: u32,
    pub removed: u32,
    pub held: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AptLine {
    pub kind: AptKind,
    pub text: String,
    pub package: Option<String>,
    pub summary: Option<AptSummary>,
}

fn strip_escapes(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    let mut chars = raw.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '\u{1b}' {
            if chars.peek() == Some(&'[') {
                chars.next();
                for n in chars.by_ref() {
                    if ('@'..='~').contains(&n) {
                        break;
                    }
                }
            } else {
                chars.next();
            }
            continue;
        }
        if c == '\t' {
            out.push(' ');
        } else if !c.is_control() {
            out.push(c);
        }
    }
    out
}

fn redact_url(token: &str) -> String {
    let Some(scheme_end) = token.find("://") else {
        return token.to_owned();
    };
    let (scheme, rest) = token.split_at(scheme_end.saturating_add(3));
    let rest = rest.split(['?', '#']).next().unwrap_or_default();
    let host_end = rest.find('/').unwrap_or(rest.len());
    let (authority, path) = rest.split_at(host_end);
    let host = authority.rsplit('@').next().unwrap_or_default();
    let marker = if authority.contains('@') { "***@" } else { "" };
    format!("{scheme}{marker}{host}{path}")
}

fn truncate(text: &str, max: usize) -> String {
    if text.len() <= max {
        return text.to_owned();
    }
    let mut end = max;
    while !text.is_char_boundary(end) {
        end = end.saturating_sub(1);
    }
    format!("{}…", &text[..end])
}

#[must_use]
pub fn sanitize(raw: &str) -> String {
    let last = raw
        .rsplit('\r')
        .find(|s| !s.trim().is_empty())
        .unwrap_or_default();
    let clean = strip_escapes(last);
    let joined = clean
        .split_whitespace()
        .map(|t| {
            if t.contains("://") {
                redact_url(t)
            } else {
                t.to_owned()
            }
        })
        .collect::<Vec<_>>()
        .join(" ");
    truncate(&joined, MAX_LINE)
}

fn package_token(raw: Option<&str>) -> Option<String> {
    let token = raw?.split(':').next()?;
    let valid = !token.is_empty()
        && token.len() <= MAX_PACKAGE
        && token
            .chars()
            .next()
            .is_some_and(|c| c.is_ascii_alphanumeric())
        && token
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '+' | '-'));
    valid.then(|| token.to_owned())
}

fn number_before(text: &str, label: &str) -> Option<u32> {
    let idx = text.find(label)?;
    text[..idx].split_whitespace().last()?.parse().ok()
}

fn summary(text: &str) -> Option<AptSummary> {
    if !text.contains(" upgraded, ") || !text.contains(" newly installed") {
        return None;
    }
    Some(AptSummary {
        upgraded: number_before(text, " upgraded,")?,
        installed: number_before(text, " newly installed").unwrap_or(0),
        removed: number_before(text, " to remove").unwrap_or(0),
        held: number_before(text, " not upgraded").unwrap_or(0),
    })
}

fn after<'a>(text: &'a str, prefix: &str) -> Option<&'a str> {
    text.strip_prefix(prefix).map(str::trim_start)
}

fn first_word(text: &str) -> Option<&str> {
    text.split_whitespace().next()
}

#[must_use]
pub fn classify(raw: &str) -> AptLine {
    let text = sanitize(raw);
    let mut package = None;
    let mut parsed = None;
    let kind = if ["Get:", "Hit:", "Ign:", "Err:"]
        .iter()
        .any(|p| text.starts_with(p))
    {
        if text.starts_with("Err:") {
            AptKind::Warn
        } else {
            AptKind::Fetch
        }
    } else if let Some(rest) = after(&text, "Unpacking ") {
        package = package_token(first_word(rest));
        AptKind::Unpack
    } else if let Some(rest) = after(&text, "Setting up ") {
        package = package_token(first_word(rest));
        AptKind::Setup
    } else if let Some(rest) = after(&text, "Processing triggers for ") {
        package = package_token(first_word(rest));
        AptKind::Trigger
    } else if text.starts_with("E: ") || text.starts_with("dpkg: error") {
        AptKind::Error
    } else if text.starts_with("W: ") || text.starts_with("N: ") {
        AptKind::Warn
    } else if ["Reading ", "Building ", "Calculating ", "Fetched "]
        .iter()
        .any(|p| text.starts_with(p))
    {
        AptKind::Read
    } else if let Some(found) = summary(&text) {
        parsed = Some(found);
        AptKind::Summary
    } else {
        AptKind::Other
    };
    AptLine {
        kind,
        text,
        package,
        summary: parsed,
    }
}

#[must_use]
pub fn upgrade_percent(summary: Option<&AptSummary>, unpacked: u32, configured: u32) -> u8 {
    let Some(s) = summary else {
        return 0;
    };
    let total = u64::from(s.upgraded).saturating_add(u64::from(s.installed));
    if total == 0 {
        return 100;
    }
    let work = u64::from(unpacked).saturating_add(u64::from(configured));
    let pct = work
        .saturating_mul(100)
        .checked_div(total.saturating_mul(2))
        .unwrap_or(100)
        .min(100);
    u8::try_from(pct).unwrap_or(100)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_escapes_and_carriage_returns() {
        assert_eq!(
            sanitize(
                "0% [Working]\r\u{1b}[33mGet:1 http://deb.debian.org/debian bookworm InRelease\u{1b}[0m\u{7}"
            ),
            "Get:1 http://deb.debian.org/debian bookworm InRelease"
        );
    }

    #[test]
    fn redacts_credentials_and_queries() {
        let line =
            sanitize("Get:2 https://user:secret@repo.example.com/apt?token=abc stable InRelease");
        assert_eq!(
            line,
            "Get:2 https://***@repo.example.com/apt stable InRelease"
        );
        assert!(!line.contains("secret") && !line.contains("token"));
    }

    #[test]
    fn truncates_on_char_boundary() {
        let long = "é".repeat(400);
        let out = sanitize(&long);
        assert!(out.len() <= MAX_LINE + 3 && out.ends_with('…'));
    }

    #[test]
    fn classifies_dpkg_lines() {
        let unpack = classify("Unpacking libc6:amd64 (2.36-9+deb12u7) over (2.36-9+deb12u4) ...");
        assert_eq!(
            (unpack.kind, unpack.package.as_deref()),
            (AptKind::Unpack, Some("libc6"))
        );
        let setup = classify("Setting up openssl (3.0.15-1~deb12u1) ...");
        assert_eq!(
            (setup.kind, setup.package.as_deref()),
            (AptKind::Setup, Some("openssl"))
        );
        assert_eq!(
            classify("Processing triggers for man-db (2.11.2-2) ...").kind,
            AptKind::Trigger
        );
        assert_eq!(classify("E: Could not get lock").kind, AptKind::Error);
        assert_eq!(classify("W: Some index files failed").kind, AptKind::Warn);
        assert_eq!(
            classify("Err:3 http://x.org stable Release").kind,
            AptKind::Warn
        );
        assert_eq!(classify("Reading package lists...").kind, AptKind::Read);
        assert_eq!(
            classify("Hit:1 http://deb.debian.org/debian bookworm InRelease").kind,
            AptKind::Fetch
        );
    }

    #[test]
    fn rejects_hostile_package_tokens() {
        assert_eq!(classify("Unpacking $(rm) (1) ...").package, None);
        assert_eq!(classify("Setting up ;x (1) ...").package, None);
    }

    #[test]
    fn parses_summary_and_progress() {
        let line = classify("3 upgraded, 1 newly installed, 2 to remove and 4 not upgraded.");
        let s = line.summary.clone();
        assert_eq!(line.kind, AptKind::Summary);
        assert_eq!(
            s,
            Some(AptSummary {
                upgraded: 3,
                installed: 1,
                removed: 2,
                held: 4
            })
        );
        assert_eq!(upgrade_percent(s.as_ref(), 4, 2), 75);
        assert_eq!(upgrade_percent(s.as_ref(), 40, 40), 100);
        assert_eq!(upgrade_percent(None, 4, 2), 0);
        let empty = AptSummary::default();
        assert_eq!(upgrade_percent(Some(&empty), 0, 0), 100);
    }
}
