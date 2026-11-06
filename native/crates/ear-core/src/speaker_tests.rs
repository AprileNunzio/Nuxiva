use crate::{VoiceBook, VoicePolicy, VoiceTracker, split_turns, valid_slug};

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

fn rows(base: &[f32], count: u64, amount: f32) -> Vec<Vec<f32>> {
    (0..count)
        .map(|i| near(base, i.saturating_add(100), amount))
        .collect()
}

#[test]
fn identifies_enrolled_people_and_rejects_strangers() {
    let (anna, luca) = (voice(1, 64), voice(2, 64));
    let mut book = VoiceBook::new(VoicePolicy::default());
    assert!(book.set_person("anna", &rows(&anna, 8, 0.3)));
    assert!(book.set_person("luca", &rows(&luca, 8, 0.3)));
    assert_eq!(
        book.verdict(&near(&anna, 7, 0.3)).slug.as_deref(),
        Some("anna")
    );
    assert_eq!(
        book.verdict(&near(&luca, 8, 0.3)).slug.as_deref(),
        Some("luca")
    );
    let stranger = book.verdict(&voice(3, 64));
    assert!(stranger.slug.is_none());
    assert_eq!(stranger.reason, "sotto soglia");
}

#[test]
fn similar_voices_need_a_larger_margin() {
    let anna = voice(1, 64);
    let sister = near(&anna, 50, 0.25);
    let mut book = VoiceBook::new(VoicePolicy::default());
    assert!(book.set_person("anna", &rows(&anna, 3, 0.05)));
    assert!(book.set_person("sara", &rows(&sister, 3, 0.05)));
    assert_eq!(book.twins(), vec![("anna".to_owned(), "sara".to_owned())]);
    let midway: Vec<f32> = anna
        .iter()
        .zip(&sister)
        .map(|(a, b)| 0.5 * (a + b))
        .collect();
    assert!(book.verdict(&midway).ambiguous);
}

#[test]
fn rejects_invalid_input() {
    let mut book = VoiceBook::new(VoicePolicy::default());
    assert!(!book.set_person("Bad Slug", &rows(&voice(1, 8), 2, 0.1)));
    assert!(!book.set_person("anna", &[]));
    assert!(!book.set_person("anna", &[vec![f32::NAN; 8]]));
    assert!(book.set_person("anna", &rows(&voice(1, 8), 2, 0.1)));
    assert!(!book.set_person("luca", &rows(&voice(2, 16), 2, 0.1)));
    assert!(book.scores(&[0.0; 4]).is_empty());
    assert!(valid_slug("ospite-2"));
    assert!(!valid_slug("-x"));
}

#[test]
fn tracker_keeps_labels_and_counts_active_voices() {
    let (a, b) = (voice(1, 32), voice(2, 32));
    let mut tracker = VoiceTracker::new();
    let first = tracker
        .observe(&a, 0.0, None)
        .unwrap_or_else(|| unreachable!());
    let again = tracker
        .observe(&near(&a, 9, 0.2), 5.0, None)
        .unwrap_or_else(|| unreachable!());
    let other = tracker
        .observe(&b, 8.0, None)
        .unwrap_or_else(|| unreachable!());
    assert!(first.new_voice && !again.new_voice && other.new_voice);
    assert_eq!(first.label, again.label);
    assert!(again.same_as_last && !other.same_as_last);
    assert_eq!(other.active_voices, 2);
    let late = tracker
        .observe(&b, 500.0, Some("luca"))
        .unwrap_or_else(|| unreachable!());
    assert_eq!(late.active_voices, 1);
    assert_eq!(late.known.as_deref(), Some("luca"));
    assert!(tracker.observe(&[f32::NAN], 1.0, None).is_none());
}

#[test]
fn split_turns_finds_a_change_of_speaker() {
    let (a, b) = (voice(1, 32), voice(2, 32));
    let windows = vec![
        near(&a, 1, 0.1),
        near(&a, 2, 0.1),
        near(&b, 3, 0.1),
        near(&b, 4, 0.1),
        near(&a, 5, 0.1),
    ];
    assert_eq!(split_turns(&windows, 0.6), vec![0, 0, 1, 1, 0]);
}
