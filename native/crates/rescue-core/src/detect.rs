use crate::signal::Kind;

const ALL_CLEAR_PHRASES: &[&str] = &[
    "sto bene",
    "tutto bene",
    "tutto a posto",
    "nessun problema",
    "falso allarme",
    "non e niente",
    "non è niente",
    "i am fine",
    "i'm fine",
    "i am ok",
    "i'm ok",
    "all good",
    "false alarm",
    "no problem",
    "never mind",
    "estoy bien",
    "todo bien",
    "falsa alarma",
    "sin problema",
    "je vais bien",
    "tout va bien",
    "fausse alerte",
    "pas de probleme",
    "pas de problème",
];

const FIRE_PHRASES: &[&str] = &[
    "al fuoco",
    "incendio",
    "sta bruciando",
    "c'è un incendio",
    "ce un incendio",
    "house on fire",
    "building on fire",
    "it's burning",
    "it is burning",
    "fuego",
    "se esta quemando",
    "se está quemando",
    "au feu",
    "ca brule",
    "ça brûle",
];

const VIOLENCE_PHRASES: &[&str] = &[
    "lasciami",
    "vattene",
    "aiuto mi aggredisce",
    "fermati",
    "leave me alone",
    "get away",
    "stop attacking",
    "don't touch me",
    "dejame",
    "déjame",
    "vete",
    "sueltame",
    "suéltame",
    "laissez-moi",
    "arrete",
    "arrête",
];

const HELP_PHRASES: &[&str] = &[
    "aiuto",
    "aiutatemi",
    "soccorso",
    "sto male",
    "mi sento male",
    "sono caduto",
    "non riesco ad alzarmi",
    "chiamate aiuto",
    "help me",
    "i fell",
    "i need help",
    "i cannot get up",
    "call for help",
    "emergency",
    "ayuda",
    "auxilio",
    "me cai",
    "me caí",
    "estoy mal",
    "no me puedo levantar",
    "au secours",
    "aidez moi",
    "aidez-moi",
    "je suis tombe",
    "je suis tombé",
    "je ne peux pas me lever",
];

#[must_use]
pub fn detect_speech(text: &str) -> (Option<Kind>, f64) {
    if text.is_empty() {
        return (None, 0.0);
    }
    let lower = text.to_lowercase();
    for phrase in ALL_CLEAR_PHRASES {
        if lower.contains(phrase) {
            return (Some(Kind::AllClear), 0.95);
        }
    }
    for phrase in FIRE_PHRASES {
        if lower.contains(phrase) {
            return (Some(Kind::Fire), 0.95);
        }
    }
    if lower.split_whitespace().any(|w| w == "fire") {
        return (Some(Kind::Fire), 0.95);
    }
    for phrase in VIOLENCE_PHRASES {
        if lower.contains(phrase) {
            return (Some(Kind::Violence), 0.90);
        }
    }
    for phrase in HELP_PHRASES {
        if lower.contains(phrase) {
            return (Some(Kind::HelpWords), 0.90);
        }
    }
    if lower.split_whitespace().any(|w| w == "help") {
        return (Some(Kind::HelpWords), 0.90);
    }
    (None, 0.0)
}

#[must_use]
pub fn detect_visual(class_name: &str, score: f64, width: f64, height: f64) -> (Option<Kind>, f64) {
    let lower = class_name.to_lowercase();
    if lower == "fall" || lower == "caduta" {
        return (Some(Kind::Fall), score.max(0.70));
    }
    if lower == "immobility" || lower == "immobilita" || lower == "immobilità" {
        return (Some(Kind::Immobility), score.max(0.65));
    }
    if (lower == "person" || lower == "persona")
        && height > 0.0
        && (width / height >= 1.6)
        && score >= 0.75
    {
        return (Some(Kind::Fall), score);
    }
    (None, 0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_speech_words() {
        assert_eq!(
            detect_speech("Aiuto sono caduto!"),
            (Some(Kind::HelpWords), 0.90)
        );
        assert_eq!(
            detect_speech("Help me please"),
            (Some(Kind::HelpWords), 0.90)
        );
        assert_eq!(
            detect_speech("Attenzione al fuoco"),
            (Some(Kind::Fire), 0.95)
        );
        assert_eq!(
            detect_speech("Tranquilli sto bene"),
            (Some(Kind::AllClear), 0.95)
        );
        assert_eq!(detect_speech("Tutto normale oggi"), (None, 0.0));
    }

    #[test]
    fn test_detect_visual_heuristics() {
        assert_eq!(
            detect_visual("fall", 0.8, 100.0, 100.0),
            (Some(Kind::Fall), 0.8)
        );
        assert_eq!(
            detect_visual("immobility", 0.7, 100.0, 100.0),
            (Some(Kind::Immobility), 0.7)
        );
        assert_eq!(
            detect_visual("person", 0.85, 320.0, 150.0),
            (Some(Kind::Fall), 0.85)
        );
        assert_eq!(detect_visual("person", 0.85, 100.0, 300.0), (None, 0.0));
    }
}
