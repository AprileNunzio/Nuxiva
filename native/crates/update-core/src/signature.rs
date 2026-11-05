use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Trusted,
    Valid,
    Unsigned,
    UnknownKey,
    Expired,
    Revoked,
    Bad,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SignatureReport {
    pub verdict: Verdict,
    pub blocking: bool,
    pub format: &'static str,
    pub fingerprint: Option<String>,
    pub signer: Option<String>,
}

const MAX_FIELD: usize = 160;

fn clean(value: &str) -> Option<String> {
    let text: String = value
        .chars()
        .filter(|c| !c.is_control())
        .take(MAX_FIELD)
        .collect();
    let trimmed = text.trim();
    (!trimmed.is_empty()).then(|| trimmed.to_owned())
}

fn report(
    verdict: Verdict,
    format: &'static str,
    fingerprint: Option<String>,
    signer: Option<String>,
) -> SignatureReport {
    SignatureReport {
        verdict,
        blocking: matches!(verdict, Verdict::Bad | Verdict::Revoked),
        format,
        fingerprint,
        signer,
    }
}

fn parse_gpg(raw: &str) -> Option<SignatureReport> {
    let mut good = false;
    let mut bad = false;
    let mut expired = false;
    let mut revoked = false;
    let mut missing = false;
    let mut trusted = false;
    let mut fingerprint = None;
    let mut signer = None;
    let mut seen = false;
    for line in raw.lines() {
        let Some(rest) = line.trim().strip_prefix("[GNUPG:] ") else {
            continue;
        };
        seen = true;
        let mut parts = rest.splitn(3, ' ');
        let keyword = parts.next().unwrap_or_default();
        let first = parts.next().unwrap_or_default();
        let tail = parts.next().unwrap_or_default();
        match keyword {
            "GOODSIG" => {
                good = true;
                signer = clean(tail);
            }
            "VALIDSIG" => fingerprint = clean(first),
            "BADSIG" => bad = true,
            "EXPSIG" | "EXPKEYSIG" => expired = true,
            "REVKEYSIG" => revoked = true,
            "NO_PUBKEY" | "ERRSIG" => missing = true,
            "TRUST_ULTIMATE" | "TRUST_FULLY" => trusted = true,
            _ => {}
        }
    }
    if !seen {
        return None;
    }
    let verdict = if bad {
        Verdict::Bad
    } else if revoked {
        Verdict::Revoked
    } else if expired {
        Verdict::Expired
    } else if good && trusted {
        Verdict::Trusted
    } else if good {
        Verdict::Valid
    } else if missing {
        Verdict::UnknownKey
    } else {
        Verdict::Unsigned
    };
    Some(report(verdict, "openpgp", fingerprint, signer))
}

fn parse_ssh(raw: &str) -> Option<SignatureReport> {
    for line in raw.lines() {
        let text = line.trim();
        if let Some(rest) = text.strip_prefix("Good \"git\" signature for ") {
            let (who, key) = rest.split_once(" with ").unwrap_or((rest, ""));
            let fingerprint = key.split_whitespace().last().and_then(clean);
            return Some(report(Verdict::Valid, "ssh", fingerprint, clean(who)));
        }
        if text.starts_with("Could not verify signature")
            || text.contains("Signature verification failed")
        {
            return Some(report(Verdict::Bad, "ssh", None, None));
        }
        if text.contains("No principal matched")
            || text.contains("allowedSignersFile needs to be configured")
        {
            return Some(report(Verdict::UnknownKey, "ssh", None, None));
        }
    }
    None
}

#[must_use]
pub fn evaluate(raw: &str, exit_code: i32) -> SignatureReport {
    if let Some(found) = parse_gpg(raw).or_else(|| parse_ssh(raw)) {
        if exit_code != 0 && matches!(found.verdict, Verdict::Trusted | Verdict::Valid) {
            return report(Verdict::Bad, found.format, found.fingerprint, found.signer);
        }
        return found;
    }
    report(Verdict::Unsigned, "none", None, None)
}

#[cfg(test)]
mod tests {
    use super::*;

    const FPR: &str = "4AEE18F83AFDEB23";

    #[test]
    fn good_trusted_signature() {
        let raw = format!(
            "[GNUPG:] NEWSIG\n[GNUPG:] GOODSIG {FPR} GitHub <noreply@github.com>\n[GNUPG:] VALIDSIG 968479A1AFF927E37D1A566BB5690EEEBB952194 2024 0\n[GNUPG:] TRUST_FULLY 0 pgp\n"
        );
        let out = evaluate(&raw, 0);
        assert_eq!(out.verdict, Verdict::Trusted);
        assert!(!out.blocking);
        assert_eq!(out.signer.as_deref(), Some("GitHub <noreply@github.com>"));
        assert_eq!(
            out.fingerprint.as_deref(),
            Some("968479A1AFF927E37D1A566BB5690EEEBB952194")
        );
    }

    #[test]
    fn bad_signature_blocks() {
        let out = evaluate(&format!("[GNUPG:] BADSIG {FPR} Mallory\n"), 1);
        assert_eq!(out.verdict, Verdict::Bad);
        assert!(out.blocking);
    }

    #[test]
    fn revoked_blocks_and_missing_key_does_not() {
        assert!(evaluate("[GNUPG:] REVKEYSIG X Y\n[GNUPG:] GOODSIG X Y\n", 0).blocking);
        let unknown = evaluate("[GNUPG:] ERRSIG X 1 8 00 1 9\n[GNUPG:] NO_PUBKEY X\n", 1);
        assert_eq!(unknown.verdict, Verdict::UnknownKey);
        assert!(!unknown.blocking);
    }

    #[test]
    fn unsigned_and_exit_code_mismatch() {
        assert_eq!(evaluate("", 1).verdict, Verdict::Unsigned);
        assert_eq!(evaluate("[GNUPG:] GOODSIG X Y\n", 1).verdict, Verdict::Bad);
    }

    #[test]
    fn ssh_signatures() {
        let ok = evaluate(
            "Good \"git\" signature for dev@example.org with ED25519 key SHA256:abc\n",
            0,
        );
        assert_eq!(ok.verdict, Verdict::Valid);
        assert_eq!(ok.format, "ssh");
        assert_eq!(ok.fingerprint.as_deref(), Some("SHA256:abc"));
        assert_eq!(
            evaluate("Signature verification failed\n", 1).verdict,
            Verdict::Bad
        );
    }

    #[test]
    fn strips_control_characters() {
        let out = evaluate("[GNUPG:] GOODSIG X Evil\u{1b}[31m Name\n", 0);
        assert_eq!(out.signer.as_deref(), Some("Evil[31m Name"));
    }
}
