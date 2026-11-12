use super::*;

fn card(id: &str, name: &str, nouns: &[&str], phrases: &[&str]) -> Card {
    Card {
        id: id.to_owned(),
        name: name.to_owned(),
        description: format!("agente {name}"),
        nouns: nouns.iter().map(|s| (*s).to_owned()).collect(),
        phrases: phrases.iter().map(|s| (*s).to_owned()).collect(),
        ..Card::default()
    }
}

fn index() -> Index {
    let mut particles = card("particles", "Particelle", &["medusa", "scultura"], &[]);
    particles.heavy = true;
    particles.risk = 3;
    let mut site = card("devstudio", "Studio", &["sito"], &[r"\bsito\b"]);
    site.project = true;
    Index::new(vec![
        card("chat", "Chat", &[], &[]),
        particles,
        card("medico", "Medico", &["battiti", "stress"], &[]),
        card("weather", "Meteo", &["meteo", "pioggia"], &[]),
        site,
    ])
}

#[test]
fn greetings_stay_with_the_assistant() {
    for text in [
        "ciao come stai",
        "Buongiorno Nuxiva!",
        "chi sei?",
        "  ",
        "hı",
    ] {
        let d = decide(&index(), text, &Learned::new());
        assert!(d.conversational, "{text}");
        assert_eq!(d.level, Level::Lampo);
    }
}

#[test]
fn nouns_route_to_the_owner() {
    let d = decide(&index(), "Mi mostri una medusa", &Learned::new());
    assert_eq!(d.primary, "particles");
    assert!(d.heavy);
    assert_eq!(d.level, Level::Standard);
    let d = decide(&index(), "quanti battiti ho", &Learned::new());
    assert_eq!(d.primary, "medico");
    assert_eq!(d.level, Level::Lampo);
}

#[test]
fn project_agents_open_a_project() {
    let d = decide(&index(), "creami un sito per la pizzeria", &Learned::new());
    assert_eq!(d.primary, "devstudio");
    assert_eq!(d.level, Level::Progetto);
}

#[test]
fn weak_requests_fall_back() {
    let d = decide(&index(), "qualcosa di strano", &Learned::new());
    assert!(d.primary.is_empty());
    assert!(!d.conversational);
    assert!((d.confidence - 0.5).abs() < f64::EPSILON);
}

#[test]
fn learning_moves_the_choice() {
    let mut learned = Learned::new();
    learned.insert(
        "nuvol".to_owned(),
        [("weather".to_owned(), 9)].into_iter().collect(),
    );
    let d = index().rank("nuvole", &learned);
    let top = d.first().map(|s| (s.id.as_str(), s.score));
    assert_eq!(top, Some(("weather", 8.0)));
}

#[test]
fn ranking_is_deterministic_and_rounded() {
    let a = index().rank("medusa scultura meteo", &Learned::new());
    let b = index().rank("meteo scultura medusa", &Learned::new());
    assert_eq!(a, b);
    for s in &a {
        assert!((s.score * 1000.0 - (s.score * 1000.0).round()).abs() < 1e-6);
    }
}

#[test]
fn hostile_phrases_and_long_input_are_contained() {
    let bad = card("bad", "Bad", &[], &["(?<=x)y", &"a".repeat(600)]);
    let idx = Index::new(vec![bad]);
    assert_eq!(idx.invalid_phrases().len(), 2);
    let long = "medusa ".repeat(10_000);
    assert!(words::clip(&long).chars().count() <= words::MAX_QUERY);
    let _ = decide(&index(), &long, &Learned::new());
}

#[test]
fn tokens_follow_the_python_rules() {
    let t = words::clean_tokens("Ciao, l’home_assistant È nel SALOTTO-2 a casa");
    let got: Vec<&str> = t.iter().map(String::as_str).collect();
    assert_eq!(got, vec!["casa", "ciao", "home_assistant", "salotto-2"]);
    assert_eq!(words::stem("salotto"), "salot");
    assert!(words::word_boundary_contains("apri vision ora", "vision"));
    assert!(!words::word_boundary_contains("television", "vision"));
}
