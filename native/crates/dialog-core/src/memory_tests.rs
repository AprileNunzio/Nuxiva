use crate::{DialogueBook, KEEP, Turn, Windows};

const NOW: f64 = 1_000_000.0;

fn book() -> DialogueBook {
    DialogueBook::new(Windows::default()).unwrap_or_else(|_| unreachable!())
}

fn turn(text: &str, reply: &str, intent: &str, ago: f64) -> Turn {
    Turn::new(text, reply, intent, NOW - ago, "")
}

#[test]
fn ellipsis_follow_ups_are_rewritten() {
    let mut b = book();
    assert!(b.remember(
        "kiosk",
        turn("che tempo fa a Roma?", "Sole.", "weather", 5.0)
    ));
    assert_eq!(
        b.resolve("kiosk", "e domani?", NOW),
        "che tempo fa a Roma domani?"
    );
    assert_eq!(
        b.resolve("kiosk", "e a Milano?", NOW),
        "che tempo fa a Milano?"
    );
    assert_eq!(
        b.resolve("kiosk", "e tu come stai?", NOW),
        "e tu come stai?"
    );
    assert_eq!(b.resolve("altro", "e domani?", NOW), "e domani?");
    b.remember(
        "kiosk",
        turn("raccontami una storia", "C'era una volta.", "chat", 1.0),
    );
    assert_eq!(b.resolve("kiosk", "e domani?", NOW), "e domani?");
}

#[test]
fn recent_turns_question_and_since_reply() {
    let mut b = book();
    assert!((b.since_reply("kiosk", NOW) - 1e9).abs() < 1.0);
    b.remember(
        "kiosk",
        turn("accendo la luce?", "Vuoi che la accenda?", "home", 10.0),
    );
    assert!(b.asked_question("kiosk", NOW));
    assert!((b.since_reply("kiosk", NOW) - 10.0).abs() < 1e-6);
    assert!(!b.asked_question("kiosk", NOW + 120.0));
    assert_eq!(b.recent("kiosk", NOW + 20.0 * 60.0), [] as [&Turn; 0]);
    for i in 0..15_u8 {
        b.remember("kiosk", turn(&format!("frase {i}"), "ok", "chat", 1.0));
    }
    assert_eq!(b.recent("kiosk", NOW).len(), KEEP);
}

#[test]
fn context_uses_speaker_names_and_resumes_after_a_pause() {
    let mut b = book();
    b.remember(
        "kiosk",
        Turn::new(
            "parliamo del viaggio in Sicilia",
            "Certo, quando parti?",
            "chat",
            NOW - 3.0 * 3600.0,
            "Nunzio",
        ),
    );
    b.remember(
        "kiosk",
        turn(
            "a giugno",
            "Giugno è perfetto.",
            "chat",
            3.0 * 3600.0 - 10.0,
        ),
    );
    let ctx = b.context("kiosk", NOW, "");
    assert!(ctx.starts_with("Conversazione ripresa dopo 180 minuti"));
    assert!(ctx.contains("Nunzio: parliamo del viaggio in Sicilia"));
    assert!(ctx.contains("Utente: a giugno"));
    assert_eq!(b.recent("kiosk", NOW), [] as [&Turn; 0]);
    let mut far = book();
    far.remember(
        "kiosk",
        turn("parliamo del viaggio", "Va bene.", "chat", 12.0 * 3600.0),
    );
    assert_eq!(far.context("kiosk", NOW, "che ore sono"), "");
    assert!(
        far.context("kiosk", NOW, "dove eravamo rimasti?")
            .contains("parliamo del viaggio")
    );
    far.remember("kiosk", turn("ciao", "Ciao!", "chat", 1.0));
    assert_eq!(far.context("kiosk", NOW, ""), "Utente: ciao\nNuxiva: Ciao!");
}

#[test]
fn load_merges_without_duplicates_and_keeps_order() {
    let mut b = book();
    let three = turn("tre", "3", "chat", 10.0);
    b.remember("kiosk", three.clone());
    assert!(b.load(
        "kiosk",
        vec![
            turn("uno", "1", "chat", 30.0),
            three,
            turn("due", "2", "chat", 20.0)
        ]
    ));
    let texts: Vec<&str> = b
        .recent("kiosk", NOW)
        .iter()
        .map(|t| t.text.as_str())
        .collect();
    assert_eq!(texts, ["uno", "due", "tre"]);
}

#[test]
fn limits_and_forget() {
    let mut b = book();
    assert!(!b.remember("", turn("x", "y", "chat", 1.0)));
    assert!(!b.remember("bad\ndevice", turn("x", "y", "chat", 1.0)));
    assert!(!b.remember(&"d".repeat(200), turn("x", "y", "chat", 1.0)));
    let long = Turn::new(
        &"a".repeat(1000),
        &"b".repeat(1000),
        "chat",
        f64::NAN,
        &"c".repeat(100),
    );
    assert_eq!(long.text.chars().count(), 400);
    assert_eq!(long.reply.chars().count(), 600);
    assert_eq!(long.who.chars().count(), 60);
    assert!(long.at.abs() < f64::EPSILON);
    for i in 0..300_u32 {
        b.remember(
            &format!("dev{i}"),
            Turn::new("x", "y", "chat", f64::from(i), ""),
        );
    }
    assert!(!b.knows("dev0"));
    assert!(b.knows("dev299"));
    assert_eq!(b.forget(Some("dev299")), 1);
    assert!(b.forget(None) > 0);
    let w = Windows {
        stale: f64::NAN,
        resume: 1.0,
        recall: 1e12,
    }
    .sanitized();
    assert!(w.stale > 0.0 && w.resume >= w.stale && w.recall >= w.resume);
}
