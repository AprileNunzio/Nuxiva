use crate::{Intent, IntentGate};

fn intent(text: &str) -> Intent {
    IntentGate::new().judge(text, false).intent
}

#[test]
fn keeps_commands_and_questions() {
    for text in [
        "accendi la luce della cucina",
        "spegni il condizionatore in camera",
        "che tempo fa domani",
        "ricordami di comprare il pane",
        "what is on my calendar today",
    ] {
        let v = IntentGate::new().judge(text, false);
        assert!(!v.drop, "{text}: {v:?}");
        assert!(v.intent.actionable(), "{text}: {v:?}");
    }
}

#[test]
fn drops_songs_chatter_and_noise() {
    for text in [
        "la la la la la oh oh oh la la la",
        "baby baby baby baby baby oh baby",
        "eh",
        "mh mh",
        "thanks for watching",
        "ieri a cena da Marco abbiamo mangiato benissimo e poi siamo usciti",
    ] {
        let v = IntentGate::new().judge(text, false);
        assert!(v.drop, "{text}: {v:?}");
    }
}

#[test]
fn repeated_lyrics_lean_to_song() {
    let text = "amore amore dammi amore e poi amore amore amore sempre amore";
    assert_eq!(intent(text), Intent::Song);
}

#[test]
fn calling_by_name_never_drops() {
    let v = IntentGate::new().judge("mh", true);
    assert!(!v.drop);
}

#[test]
fn empty_and_huge_inputs_are_safe() {
    let gate = IntentGate::new();
    assert!(gate.judge("   ", false).drop);
    let huge = "ciao ".repeat(50_000);
    let v = gate.judge(&huge, false);
    assert!(v.confidence.is_finite());
}
