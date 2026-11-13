use std::fmt::Write;

use crate::{MAX_INPUT, MAX_LINES, MAX_TEXT, MAX_WORDS, SongClock, parse};

#[test]
fn parses_basic_lines_sorted() {
    let lines = parse("[00:12.50]Seconda\n[00:01.2]Prima\n[ar:Artista]\nsenza tempo\n");
    let got: Vec<(u32, &str)> = lines.iter().map(|l| (l.t_ms, l.text.as_str())).collect();
    assert_eq!(got, vec![(1_200, "Prima"), (12_500, "Seconda")]);
}

#[test]
fn fraction_lengths_and_colon_separator() {
    let lines = parse("[01:02.5]a\n[01:02.05]b\n[01:02.005]c\n[01:02:50]d\n[1:02]e");
    let times: Vec<u32> = lines.iter().map(|l| l.t_ms).collect();
    assert_eq!(times, vec![62_000, 62_005, 62_050, 62_500, 62_500]);
}

#[test]
fn repeated_stamps_duplicate_the_line() {
    let lines = parse("[00:10.00][00:40.00]Ritornello");
    assert_eq!(lines.len(), 2);
    assert!(
        lines
            .iter()
            .all(|l| l.text == "Ritornello" && l.words.is_empty())
    );
    assert_eq!(lines.get(1).map(|l| l.t_ms), Some(40_000));
}

#[test]
fn invalid_stamps_are_ignored() {
    let lines = parse("[00:75.00]no\n[aa:10]no\n[0000:10]no\n[00:1]no\n[00:10.1234]no\n[00:05]si");
    assert_eq!(lines.len(), 1);
    assert_eq!(lines.first().map(|l| l.text.as_str()), Some("si"));
}

#[test]
fn offset_tag_moves_every_line() {
    let lines = parse("[offset:+500]\n[00:10.00]a <00:10.20>b\n[00:00.20]c");
    assert_eq!(lines.first().map(|l| l.t_ms), Some(0));
    let second = lines.get(1).cloned().unwrap_or_else(|| crate::LyricLine {
        t_ms: 0,
        text: String::new(),
        words: Vec::new(),
    });
    assert_eq!(second.t_ms, 9_500);
    assert_eq!(second.words.first().map(|w| w.t_ms), Some(9_700));
    let late = parse("[offset:-250]\n[00:01.00]x");
    assert_eq!(late.first().map(|l| l.t_ms), Some(1_250));
}

#[test]
fn enhanced_words_are_split() {
    let lines = parse("[00:05.00]<00:05.00>Nel <00:05.40>blu <00:06.10>dipinto");
    let line = lines.first().cloned().unwrap_or_else(|| crate::LyricLine {
        t_ms: 0,
        text: String::new(),
        words: Vec::new(),
    });
    assert_eq!(line.text, "Nel blu dipinto");
    let words: Vec<(u32, &str)> = line
        .words
        .iter()
        .map(|w| (w.t_ms, w.text.as_str()))
        .collect();
    assert_eq!(
        words,
        vec![(5_000, "Nel"), (5_400, "blu"), (6_100, "dipinto")]
    );
}

#[test]
fn literal_angle_brackets_survive() {
    let lines = parse("[00:01.00]a < b <tag> c");
    assert_eq!(
        lines.first().map(|l| l.text.as_str()),
        Some("a < b <tag> c")
    );
}

#[test]
fn control_characters_and_spaces_are_cleaned() {
    let lines = parse("[00:01.00]  ciao\u{7}\tmondo   bello \r\n");
    assert_eq!(
        lines.first().map(|l| l.text.as_str()),
        Some("ciao mondo bello")
    );
}

#[test]
fn empty_text_lines_are_pauses() {
    let lines = parse("[00:01.00]\n[00:02.00]x");
    assert_eq!(lines.first().map(|l| l.text.is_empty()), Some(true));
}

#[test]
fn limits_are_enforced() {
    let long = "x".repeat(1_000);
    let lines = parse(&format!("[00:01.00]{long}"));
    assert_eq!(
        lines.first().map(|l| l.text.chars().count()),
        Some(MAX_TEXT)
    );
    let mut many = String::new();
    for i in 0..1_000 {
        let _ = writeln!(many, "[{:02}:{:02}.00]r{i}", i / 60 % 100, i % 60);
    }
    assert_eq!(parse(&many).len(), MAX_LINES);
    let mut words = String::new();
    for i in 0..200 {
        let _ = write!(words, "<00:{:02}.00>w{i} ", i % 60);
    }
    let line = parse(&format!("[00:00.00]{words}"));
    assert_eq!(line.first().map(|l| l.words.len()), Some(MAX_WORDS));
    let huge = format!("{}\n[00:01.00]dopo", "é".repeat(MAX_INPUT));
    assert!(parse(&huge).is_empty());
}

#[test]
fn clock_first_observation_sets_origin() {
    let mut clock = SongClock::new();
    let r = clock.observe(100_000, 30_000);
    assert_eq!(r.origin_ms, 70_000);
    assert!(r.jumped);
    assert_eq!(clock.position(110_000), Some(40_000));
}

#[test]
fn clock_smooths_small_errors() {
    let mut clock = SongClock::new();
    clock.observe(100_000, 30_000);
    let r = clock.observe(160_000, 89_400);
    assert_eq!(r.origin_ms, 70_300);
    assert_eq!(r.correction_ms, 300);
    let r = clock.observe(220_000, 149_700);
    assert_eq!(r.origin_ms, 70_300);
}

#[test]
fn clock_needs_two_agreeing_observations_to_jump() {
    let mut clock = SongClock::new();
    clock.observe(100_000, 30_000);
    let outlier = clock.observe(150_000, 10_000);
    assert_eq!(outlier.origin_ms, 70_000);
    assert!(!outlier.jumped);
    let confirm = clock.observe(160_000, 20_400);
    assert!(confirm.jumped);
    assert_eq!(confirm.origin_ms, 139_800);
}

#[test]
fn clock_negative_errors_truncate_toward_zero() {
    let mut clock = SongClock::new();
    clock.observe(10_000, 0);
    let r = clock.observe(20_000, 10_001);
    assert_eq!(r.correction_ms, 0);
    let r = clock.observe(30_000, 20_007);
    assert_eq!(r.correction_ms, -2);
}

#[test]
fn clock_reset_forgets() {
    let mut clock = SongClock::new();
    clock.observe(1, 0);
    clock.reset();
    assert_eq!(clock.origin(), None);
    assert_eq!(clock.position(5), None);
}
