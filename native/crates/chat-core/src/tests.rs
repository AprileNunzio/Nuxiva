use crate::{CONVERSATION, IntentError, IntentTable};

type Check = Result<(), IntentError>;

#[test]
fn every_pattern_compiles() -> Check {
    assert_eq!(IntentTable::new()?.names().count(), 16);
    Ok(())
}

#[test]
fn detects_each_family() -> Check {
    let table = IntentTable::new()?;
    let cases = [
        ("che tempo fa domani", "weather"),
        ("chi canta questa canzone", "music"),
        ("cosa stai studiando", "study"),
        ("mostrami la memoria", "brain"),
        ("stato del sistema", "system"),
        ("accendi la webcam", "camera"),
        ("chi vedi", "vision"),
        ("scansiona la rete", "network"),
        ("abito a Roma", "place"),
        ("quanti anni ho", "person_info"),
        ("mi chiamo Luca", "introduce"),
        ("che voci hai", "voices"),
        ("è passato il corriere", "ask_evidence"),
        ("stato soccorso", "rescue"),
        ("dispositivi matter", "matter"),
        ("che ore sono", "time"),
    ];
    for (text, expected) in cases {
        assert_eq!(table.detect(text).name, expected, "{text}");
    }
    Ok(())
}

#[test]
fn falls_back_to_conversation() -> Check {
    let table = IntentTable::new()?;
    assert_eq!(table.detect("raccontami una storia").name, CONVERSATION);
    assert_eq!(table.detect("").name, CONVERSATION);
    Ok(())
}

#[test]
fn first_match_wins_and_case_is_ignored() -> Check {
    let table = IntentTable::new()?;
    assert_eq!(table.detect("METEO e che ore sono").name, "weather");
    assert_eq!(table.detect("CHE ORE SONO").name, "time");
    Ok(())
}

#[test]
fn hostile_input_is_linear() -> Check {
    let table = IntentTable::new()?;
    let long = "a ".repeat(200_000);
    assert_eq!(table.detect(&long).name, CONVERSATION);
    assert_eq!(table.detect("\u{0}che\u{0}ore sono").name, CONVERSATION);
    Ok(())
}
