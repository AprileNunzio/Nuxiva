use std::collections::HashSet;

use crate::words::{Lexicon, Segment, Token, assess, fold, phonetic, similarity};

fn tokens(parts: &[(&str, f64)]) -> Vec<Token> {
    parts
        .iter()
        .map(|(t, p)| Token {
            text: (*t).to_owned(),
            prob: *p,
        })
        .collect()
}

fn lexicon() -> Lexicon {
    let terms: Vec<String> = [
        "Nuxiva",
        "Nunzio",
        "Giulia",
        "Soggiorno",
        "Lampada Arco",
        "Camera di Marco",
        "Ciabatta TV",
    ]
    .iter()
    .map(|s| (*s).to_owned())
    .collect();
    Lexicon::new(&terms)
}

#[test]
fn folding_and_phonetic_keys() {
    assert_eq!(fold("  Perché  l'ÀNCORA-blu "), "perche l ancora blu");
    assert_eq!(phonetic("Chiara"), phonetic("Kiara"));
    assert_eq!(phonetic("Giulia"), phonetic("Julia"));
    assert_eq!(phonetic("ciao"), "cao");
    assert_eq!(phonetic("gnocchi"), "nokki".replace("kk", "k"));
    assert_eq!(phonetic("Nuxiva"), phonetic("nuksiva"));
    assert!(
        similarity("Nuxiva", "nuksiva") > 0.85,
        "{}",
        similarity("Nuxiva", "nuksiva")
    );
    assert!(similarity("Nuxiva", "pizza") < 0.6);
}

#[test]
fn misheard_names_with_low_confidence_are_fixed() {
    let lex = lexicon();
    let none = HashSet::new();
    let (text, fixes) = lex.correct(
        &tokens(&[
            (" Accendi", 0.95),
            (" la", 0.97),
            (" lampada", 0.6),
            (" arcò", 0.3),
            (".", 0.9),
        ]),
        &none,
    );
    assert_eq!(text, " Accendi la Lampada Arco.");
    assert_eq!(fixes.len(), 1);
    let (text, _) = lex.correct(
        &tokens(&[(" Dove", 0.9), (" è", 0.9), (" Nunsio", 0.35), ("?", 0.9)]),
        &none,
    );
    assert_eq!(text, " Dove è Nunzio?");
    let (text, _) = lex.correct(&tokens(&[(" Ciao", 0.9), (" Giuglia", 0.4)]), &none);
    assert_eq!(text, " Ciao Giulia");
}

#[test]
fn confident_or_unrelated_words_are_left_alone() {
    let lex = lexicon();
    let none = HashSet::new();
    let input = tokens(&[
        (" Che", 0.95),
        (" tempo", 0.95),
        (" fa", 0.9),
        (" a", 0.9),
        (" marzo", 0.92),
        ("?", 0.9),
    ]);
    let (text, fixes) = lex.correct(&input, &none);
    assert_eq!(text, " Che tempo fa a marzo?");
    assert_eq!(fixes, [] as [crate::words::Correction; 0]);
    let (text, fixes) = lex.correct(&tokens(&[(" Nunzio", 0.2), (" mangia", 0.3)]), &none);
    assert_eq!(text, " Nunzio mangia");
    assert_eq!(fixes, [] as [crate::words::Correction; 0]);
    assert!(Lexicon::new(&["ab".to_owned(), "x".repeat(200)]).is_empty());
}

#[test]
fn context_lowers_the_bar_a_little() {
    let lex = lexicon();
    let heard = tokens(&[(" accendi", 0.9), (" soggiono", 0.7)]);
    let (plain, _) = lex.correct(&heard, &HashSet::new());
    let context: HashSet<String> = ["soggiorno".to_owned()].into_iter().collect();
    let (boosted, fixes) = lex.correct(&heard, &context);
    assert_eq!(boosted, " accendi Soggiorno");
    assert!(fixes.len() == 1 && (plain == boosted || plain == " accendi soggiono"));
}

#[test]
fn hallucinations_are_flagged() {
    let seg = |text: &str, lp: f64, ns: f64, cr: f64| Segment {
        text: text.to_owned(),
        avg_logprob: lp,
        no_speech_prob: ns,
        compression_ratio: cr,
    };
    let phrases: HashSet<String> = ["sottotitoli a cura di qtss".to_owned()]
        .into_iter()
        .collect();
    let out = assess(
        &[
            seg("accendi la luce", -0.2, 0.05, 1.2),
            seg("grazie grazie grazie grazie grazie", -0.4, 0.1, 1.9),
            seg("Sottotitoli a cura di QTSS", -0.3, 0.2, 1.0),
            seg("boh", -1.4, 0.8, 1.0),
            seg("assistente digitale", -0.9, 0.3, 1.0),
            seg("ok", f64::NAN, 0.1, 1.0),
            seg("la la la la la la la la", -0.3, 0.1, 3.0),
        ],
        "Ehi, Nuxiva, assistente digitale.",
        &phrases,
    );
    assert_eq!(out.keep, [true, false, false, false, false, false, false]);
    assert_eq!(out.reasons.get(3), Some(&"silenzio"));
    assert!((out.confidence - (-0.2_f64).exp()).abs() < 1e-9);
}
