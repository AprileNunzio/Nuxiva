use crate::{AttributionPolicy, Attributor, Evidence, VoiceBook, VoicePolicy, WindowVerdict};

fn voice(seed: u64, dim: usize) -> Vec<f32> {
    let mut state = seed.wrapping_mul(6_364_136_223_846_793_005).wrapping_add(1);
    (0..dim)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            #[allow(clippy::cast_precision_loss)]
            let v = (state >> 40) as f32 / (1u64 << 24) as f32 - 0.5;
            v
        })
        .collect()
}

fn near(base: &[f32], seed: u64, amount: f32) -> Vec<f32> {
    base.iter()
        .zip(voice(seed, base.len()))
        .map(|(b, n)| b + amount * n)
        .collect()
}

fn book(owner: &[f32]) -> VoiceBook {
    let mut book = VoiceBook::new(VoicePolicy::default());
    let rows: Vec<Vec<f32>> = (0..8_u64)
        .map(|i| near(owner, i.saturating_add(100), 0.2))
        .collect();
    assert!(book.set_person("nunzio", &rows));
    book
}

fn judge(
    gate: &mut Attributor,
    book: &VoiceBook,
    probe: &[f32],
    seconds: f32,
    programme: bool,
    windows: &[WindowVerdict],
    now: f64,
) -> crate::Attribution {
    let verdict = book.verdict(probe);
    let limit = book.limit("nunzio").unwrap_or(0.62);
    gate.judge(&Evidence {
        probe,
        slug: verdict.slug.as_deref(),
        score: verdict.score,
        limit,
        seconds,
        programme,
        windows,
        now,
    })
}

#[test]
fn the_owner_is_verified() {
    let owner = voice(1, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    let out = judge(
        &mut gate,
        &book,
        &near(&owner, 7, 0.2),
        3.0,
        false,
        &[],
        0.0,
    );
    assert!(out.verified, "{out:?}");
    assert_eq!(out.slug.as_deref(), Some("nunzio"));
}

#[test]
fn a_short_segment_is_never_attributed() {
    let owner = voice(1, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    let out = judge(
        &mut gate,
        &book,
        &near(&owner, 7, 0.1),
        0.6,
        false,
        &[],
        0.0,
    );
    assert!(!out.verified);
    assert_eq!(out.reason, "troppo breve");
}

#[test]
fn a_borderline_voice_is_refused_instead_of_guessed() {
    let owner = voice(1, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    let mut refused = 0;
    let mut accepted_by_book = 0;
    for seed in 0..200 {
        let probe = near(&owner, 1_000 + seed, 1.4);
        let verdict = book.verdict(&probe);
        if verdict.slug.is_some() {
            accepted_by_book += 1;
            if !judge(&mut gate, &book, &probe, 3.0, false, &[], 0.0).verified {
                refused += 1;
            }
        }
    }
    assert!(accepted_by_book > 0);
    assert!(
        refused > 0,
        "no borderline refused out of {accepted_by_book}"
    );
}

#[test]
fn programme_audio_raises_the_bar() {
    let owner = voice(1, 64);
    let book = book(&owner);
    let mut calm = Attributor::new(AttributionPolicy::default());
    let mut busy = Attributor::new(AttributionPolicy::default());
    let mut separated = 0;
    for seed in 0..300 {
        let probe = near(&owner, 2_000 + seed, 0.9);
        let a = judge(&mut calm, &book, &probe, 3.0, false, &[], 0.0);
        let b = judge(&mut busy, &book, &probe, 3.0, true, &[], 0.0);
        assert!(!b.verified || a.verified);
        if a.verified && !b.verified {
            separated += 1;
        }
    }
    assert!(separated > 0);
}

#[test]
fn a_repeating_foreign_voice_is_remembered_and_blocked() {
    let owner = voice(1, 64);
    let radio = voice(9, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    for i in 0..4_u64 {
        let out = judge(
            &mut gate,
            &book,
            &near(&radio, i.saturating_add(50), 0.2),
            4.0,
            false,
            &[],
            #[allow(clippy::cast_precision_loss)]
            {
                i as f64
            },
        );
        assert!(!out.verified);
    }
    assert!(gate.foreign_count() >= 1);
    let blended: Vec<f32> = owner
        .iter()
        .zip(&radio)
        .map(|(a, b)| 0.55 * a + 0.45 * b)
        .collect();
    let out = judge(
        &mut gate,
        &book,
        &near(&blended, 77, 0.05),
        4.0,
        false,
        &[],
        10.0,
    );
    assert!(!out.verified, "{out:?}");
}

#[test]
fn mixed_windows_are_refused() {
    let owner = voice(1, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    let windows = [
        WindowVerdict {
            slug: Some("nunzio".into()),
            score: 0.8,
        },
        WindowVerdict {
            slug: None,
            score: 0.2,
        },
    ];
    let out = judge(
        &mut gate,
        &book,
        &near(&owner, 7, 0.1),
        4.0,
        false,
        &windows,
        0.0,
    );
    assert!(!out.verified);
    assert_eq!(out.reason, "voci miste o incerte");
}

#[test]
fn a_sudden_change_inside_a_session_is_refused() {
    let owner = voice(1, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    assert!(
        judge(
            &mut gate,
            &book,
            &near(&owner, 7, 0.1),
            4.0,
            false,
            &[],
            0.0
        )
        .verified
    );
    let drifted = Evidence {
        probe: &voice(5, 64),
        slug: Some("nunzio"),
        score: 0.95,
        limit: 0.62,
        seconds: 4.0,
        programme: false,
        windows: &[],
        now: 3.0,
    };
    let out = gate.judge(&drifted);
    assert!(!out.verified);
    assert_eq!(out.reason, "cambio di voce nella sessione");
}

#[test]
fn invalid_input_is_refused() {
    let mut gate = Attributor::new(AttributionPolicy::default());
    let nan = [f32::NAN; 4];
    let out = gate.judge(&Evidence {
        probe: &nan,
        slug: Some("nunzio"),
        score: 0.9,
        limit: 0.6,
        seconds: 3.0,
        programme: false,
        windows: &[],
        now: 0.0,
    });
    assert!(!out.verified);
    assert_eq!(out.reason, "dati non validi");
}

#[test]
fn recurring_foreign_voices_count_as_a_programme() {
    let owner = voice(1, 64);
    let radio = voice(9, 64);
    let book = book(&owner);
    let mut gate = Attributor::new(AttributionPolicy::default());
    assert_eq!(gate.foreign_recent(0.0, 120.0), 0);
    for i in 0..4_u64 {
        #[allow(clippy::cast_precision_loss)]
        let now = i as f64;
        judge(
            &mut gate,
            &book,
            &near(&radio, i.saturating_add(50), 0.2),
            4.0,
            false,
            &[],
            now,
        );
    }
    assert_eq!(gate.foreign_recent(5.0, 120.0), 1);
    assert_eq!(gate.foreign_recent(500.0, 120.0), 0);
}
