use crate::{FrameMeta, Policy, PushOutcome, Rejection, Source, VisualBuffer};

fn meta(app: &str, title: &str, at_ms: u64) -> FrameMeta {
    FrameMeta {
        source: Source::Screen,
        app: app.to_owned(),
        title: title.to_owned(),
        at_ms,
    }
}

fn vec_of(seed: usize) -> Vec<f32> {
    (0..32)
        .map(|i| if i % 7 == seed % 7 { 1.0 } else { 0.05 })
        .collect()
}

fn consenting() -> VisualBuffer {
    VisualBuffer::new(Policy {
        consent: true,
        ..Policy::default()
    })
}

#[test]
fn nothing_is_stored_without_consent() {
    let mut buf = VisualBuffer::new(Policy::default());
    assert_eq!(
        buf.push(&meta("code", "main.rs", 0), &vec_of(1)),
        PushOutcome::Rejected(Rejection::NoConsent)
    );
    assert!(buf.is_empty());
    assert!(!buf.indicator(0).active);
}

#[test]
fn sensitive_windows_are_never_buffered() {
    let mut buf = consenting();
    for (app, title) in [
        ("1Password", "Vault"),
        ("Firefox", "Home Banking - Banca Intesa"),
        ("Chrome", "PayPal: accesso"),
        ("Firefox", "Navigazione in incognito"),
    ] {
        assert_eq!(
            buf.push(&meta(app, title, 10_000), &vec_of(2)),
            PushOutcome::Rejected(Rejection::Sensitive),
            "{app} {title}"
        );
    }
    assert!(buf.is_empty());
}

#[test]
fn rate_limit_expiry_and_capacity() {
    let mut buf = consenting();
    assert_eq!(
        buf.push(&meta("code", "a", 0), &vec_of(1)),
        PushOutcome::Stored
    );
    assert_eq!(
        buf.push(&meta("code", "a", 500), &vec_of(1)),
        PushOutcome::Rejected(Rejection::TooSoon)
    );
    assert_eq!(
        buf.push(&meta("code", "a", 2_500), &vec_of(2)),
        PushOutcome::Stored
    );
    buf.expire(2_500 + 6 * 60_000);
    assert!(buf.is_empty());
    let mut small = VisualBuffer::new(Policy {
        consent: true,
        capacity: 8,
        interval_ms: 250,
        ..Policy::default()
    });
    for i in 0..20_u64 {
        let _ = small.push(
            &meta("code", "a", i * 300),
            &vec_of(usize::try_from(i).unwrap_or(0)),
        );
    }
    assert_eq!(small.len(), 8);
}

#[test]
fn invalid_embeddings_are_rejected() {
    let mut buf = consenting();
    assert_eq!(
        buf.push(&meta("code", "a", 0), &[f32::NAN; 8]),
        PushOutcome::Rejected(Rejection::Invalid)
    );
    assert_eq!(
        buf.push(&meta("code", "a", 0), &[0.0; 8]),
        PushOutcome::Rejected(Rejection::Invalid)
    );
    assert_eq!(
        buf.push(&meta("code", "a", 0), &vec_of(1)),
        PushOutcome::Stored
    );
    assert_eq!(
        buf.push(&meta("code", "a", 5_000), &[1.0; 8]),
        PushOutcome::Rejected(Rejection::Invalid)
    );
}

#[test]
fn query_context_and_revoke() {
    let mut buf = consenting();
    let _ = buf.push(&meta("editor", "a", 0), &vec_of(1));
    let _ = buf.push(&meta("browser", "b", 3_000), &vec_of(2));
    let hits = buf.query(&vec_of(1), 4_000, 2);
    assert_eq!(hits.first().map(|h| h.app.as_str()), Some("editor"));
    assert_eq!(buf.current_app(4_000), Some("browser"));
    assert!(buf.context(4_000).is_some());
    assert!(buf.indicator(4_000).active);
    buf.set_policy(Policy::default());
    assert!(buf.is_empty());
    assert!(buf.context(4_000).is_none());
}
