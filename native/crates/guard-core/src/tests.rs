use crate::{
    LoginLimiter, MAX_ATTEMPTS, MAX_TRACKED, OriginRequest, OriginVerdict, RedirectRequest,
    SessionCodec, decode_value, entries, format_line, normalize, normalize_name, redirect_target,
    safe_host, verdict,
};

const SECRET: &[u8] = b"0123456789abcdef0123456789abcdef";

fn codec() -> Result<SessionCodec, crate::GuardError> {
    SessionCodec::new(SECRET)
}

#[test]
fn session_round_trip_and_tamper() -> Result<(), crate::GuardError> {
    let codec = codec()?;
    let token = codec.issue("admin", 1_000, 60)?;
    assert_eq!(codec.verify(&token, 1_030.0).as_deref(), Some("admin"));
    assert_eq!(codec.verify(&token, 1_060.0).as_deref(), Some("admin"));
    assert_eq!(codec.verify(&token, 1_060.5), None);
    let mut chars: Vec<char> = token.chars().collect();
    if let Some(first) = chars.first_mut() {
        *first = if *first == 'A' { 'B' } else { 'A' };
    }
    let forged: String = chars.into_iter().collect();
    assert_eq!(codec.verify(&forged, 1_000.0), None);
    let other = SessionCodec::new(b"ffffffffffffffffffffffffffffffff")?;
    assert_eq!(other.verify(&token, 1_000.0), None);
    Ok(())
}

#[test]
fn session_rejects_bad_input() -> Result<(), crate::GuardError> {
    assert!(SessionCodec::new(b"short").is_err());
    let codec = codec()?;
    assert!(codec.issue("", 0, 60).is_err());
    assert!(codec.issue("a", 0, 0).is_err());
    assert!(codec.issue("a", i64::MAX, 60).is_err());
    assert_eq!(codec.verify("", 0.0), None);
    assert_eq!(codec.verify("!!!", 0.0), None);
    assert_eq!(codec.verify(&"A".repeat(5000), 0.0), None);
    let pipe = codec.issue("a|b", 0, 60)?;
    assert_eq!(codec.verify(&pipe, 0.0).as_deref(), Some("a|b"));
    Ok(())
}

#[test]
fn limiter_blocks_after_attempts_and_is_bounded() {
    let mut limiter = LoginLimiter::new();
    for i in 0..MAX_ATTEMPTS {
        assert!(!limiter.limited("1.2.3.4", 10.0));
        limiter.fail(
            "1.2.3.4",
            10.0 + f64::from(u32::try_from(i).unwrap_or_default()),
        );
    }
    assert!(limiter.limited("1.2.3.4", 20.0));
    assert!(!limiter.limited("1.2.3.4", 400.0));
    for i in 0..(MAX_TRACKED + 50) {
        limiter.fail(&format!("10.0.{}.{}", i / 256, i % 256), 500.0);
    }
    assert!(limiter.tracked() <= MAX_TRACKED);
}

fn req<'a>(host: &'a str, method: &'a str, site: &'a str, origin: &'a str) -> OriginRequest<'a> {
    OriginRequest {
        host,
        method,
        fetch_site: site,
        origin,
    }
}

#[test]
fn origin_verdicts() {
    let trusted = vec!["localhost".to_owned(), "box".to_owned()];
    assert_eq!(
        verdict(req("box:8080", "GET", "", ""), &trusted),
        OriginVerdict::Allow
    );
    assert_eq!(
        verdict(req("evil.com", "GET", "", ""), &trusted),
        OriginVerdict::UntrustedHost
    );
    assert_eq!(
        verdict(req("[::1]:80", "POST", "", ""), &trusted),
        OriginVerdict::Allow
    );
    assert_eq!(
        verdict(req("[::1", "GET", "", ""), &trusted),
        OriginVerdict::UntrustedHost
    );
    assert_eq!(
        verdict(req("box", "POST", "cross-site", ""), &trusted),
        OriginVerdict::CrossSite
    );
    assert_eq!(
        verdict(req("box", "post", "", "https://evil.com"), &trusted),
        OriginVerdict::ForeignOrigin
    );
    assert_eq!(
        verdict(
            req("box:80", "DELETE", "same-origin", "http://BOX:80"),
            &trusted
        ),
        OriginVerdict::Allow
    );
    assert_eq!(
        verdict(req("", "POST", "", ""), &trusted),
        OriginVerdict::Allow
    );
    assert_eq!(
        verdict(req("nas.local", "GET", "", ""), &trusted),
        OriginVerdict::Allow
    );
}

#[test]
fn safe_hosts() {
    assert_eq!(safe_host(" Box.Local:8080 "), "box.local");
    assert_eq!(safe_host("[0:0:0:0:0:0:0:1]:443"), "[::1]");
    assert_eq!(safe_host("[::ffff:1.2.3.4]"), "[::ffff:102:304]");
    assert_eq!(safe_host("[1:0:0:2:0:0:0:3]"), "[1:0:0:2::3]");
    assert_eq!(safe_host("evil..com"), "");
    assert_eq!(safe_host("-x"), "");
    assert_eq!(safe_host("a b"), "");
    assert_eq!(safe_host("host:123456"), "");
    assert_eq!(safe_host("192.168.1.5:80"), "192.168.1.5");
}

#[test]
fn redirect_targets() {
    let base = RedirectRequest {
        scheme: "http",
        client: "192.168.1.9",
        path: "/a b/é",
        method: "GET",
        fetch_mode: "navigate",
        accept: "",
        host: "nuxiva.local:8080",
        query: b"x=1&y=\xe9",
    };
    assert_eq!(
        redirect_target(&base, true, 8443),
        "https://nuxiva.local:8443/admin/a%20b/%C3%A9?x=1&y=%C3%A9"
    );
    assert_eq!(
        redirect_target(&RedirectRequest { query: b"", ..base }, false, 443),
        "https://nuxiva.local/a%20b/%C3%A9"
    );
    assert_eq!(
        redirect_target(
            &RedirectRequest {
                client: "::1",
                ..base
            },
            false,
            443
        ),
        ""
    );
    assert_eq!(
        redirect_target(
            &RedirectRequest {
                path: "/healthz",
                ..base
            },
            false,
            443
        ),
        ""
    );
    assert_eq!(
        redirect_target(
            &RedirectRequest {
                method: "POST",
                ..base
            },
            false,
            443
        ),
        ""
    );
    assert_eq!(redirect_target(&base, false, 0), "");
    let html = RedirectRequest {
        fetch_mode: "",
        accept: "text/HTML",
        ..base
    };
    assert!(!redirect_target(&html, false, 443).is_empty());
}

#[test]
fn env_round_trip() -> Result<(), crate::GuardError> {
    assert_eq!(
        format_line("KEY", "a\"b$c\\é\t")?,
        "KEY=\"a\\\"b\\$c\\\\é\\t\""
    );
    assert!(format_line("1KEY", "x").is_err());
    assert!(format_line("KEY", "a\nb").is_err());
    assert_eq!(decode_value("  \"a\\\"b\\$c\"  "), "a\"b$c");
    assert_eq!(decode_value("'\"x\"'"), "x");
    assert_eq!(decode_value("\"a\" \"b\""), "a\" \"b");
    assert_eq!(decode_value("plain"), "plain");
    assert_eq!(decode_value("\"\\ud83d\\ude00\""), "😀");
    let parsed = entries("# c\nA=1\r\nA=2\n'B'=\"x y\"\nbad line\n9X=1");
    assert_eq!(parsed.len(), 3);
    assert_eq!(normalize("# c\nA=1\nB='q'")?, "# c\nA=\"1\"\nB=\"q\"\n");
    Ok(())
}

#[test]
fn assistant_names() {
    assert_eq!(normalize_name("  hey   jarvis  "), "jarvis");
    assert_eq!(normalize_name("OKAY Friday"), "Friday");
    assert_eq!(normalize_name("ok"), "ok");
    assert_eq!(normalize_name("MAX"), "Max");
    assert_eq!(normalize_name("<script>"), "script");
    assert_eq!(normalize_name("!!!"), "Nuxiva");
    assert_eq!(normalize_name("ｎｕｘ"), "nux");
    assert_eq!(normalize_name(&"a".repeat(50)).chars().count(), 32);
    assert_eq!(normalize_name("Anna   Maria"), "Anna Maria");
}
