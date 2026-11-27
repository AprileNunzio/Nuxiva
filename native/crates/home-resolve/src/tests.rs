use crate::{Decision, Request, Resolution, Resolver, distance, normalize, similarity, stem};

const HOME: &str = r#"{
  "areas": [
    {"id": "camera_letto", "name": "Camera da letto"},
    {"id": "camera_ospiti", "name": "Camera ospiti"},
    {"id": "cucina", "name": "Cucina"},
    {"id": "soggiorno", "name": "Soggiorno", "aliases": ["Sala"]},
    {"id": "bagno", "name": "Bagno"},
    {"id": "studio", "name": "Studio"}
  ],
  "entities": [
    {"id": "light.plafoniera", "domain": "light", "name": "Plafoniera", "area": "camera_letto", "device": "d1"},
    {"id": "light.abat_jour", "domain": "light", "name": "Abat-jour comodino", "area": "camera_letto", "device": "d2"},
    {"id": "cover.camera", "domain": "cover", "name": "Tapparella camera", "area": "camera_letto"},
    {"id": "light.ospiti", "domain": "light", "name": "Luce ospiti", "area": "camera_ospiti"},
    {"id": "light.cucina", "domain": "light", "name": "Luce cucina", "area": "cucina", "device": "d3"},
    {"id": "light.led_cucina", "domain": "light", "name": "Striscia LED", "area": "cucina", "device": "d4"},
    {"id": "switch.caffe", "domain": "switch", "name": "Macchina del caffè", "area": "cucina"},
    {"id": "light.lampadario", "domain": "light", "name": "Lampadario", "area": "soggiorno"},
    {"id": "cover.soggiorno", "domain": "cover", "name": "Tapparella soggiorno", "area": "soggiorno"},
    {"id": "media_player.tv", "domain": "media_player", "name": "TV Samsung", "area": "soggiorno"},
    {"id": "light.bagno", "domain": "light", "name": "Luce bagno", "area": "bagno", "device": "d5"},
    {"id": "switch.bagno", "domain": "switch", "name": "Luce bagno relè", "area": "bagno", "device": "d5", "as_light": true},
    {"id": "climate.studio", "domain": "climate", "name": "Condizionatore studio", "area": "studio"},
    {"id": "fan.studio", "domain": "fan", "name": "Ventilatore", "area": "studio"},
    {"id": "lock.porta", "domain": "lock", "name": "Serratura ingresso"}
  ]
}"#;

const BEDROOM: &[&str] = &["light.abat_jour", "light.plafoniera"];

pub(crate) fn resolver() -> Resolver {
    Resolver::from_json(HOME).expect("inventory")
}

fn ask(text: &str) -> Resolution {
    resolver()
        .resolve(&Request {
            text: text.to_owned(),
            ..Request::default()
        })
        .expect("resolve")
}

fn ask_here(text: &str, here: &str) -> Resolution {
    resolver()
        .resolve(&Request {
            text: text.to_owned(),
            here: Some(here.to_owned()),
            fallback: None,
        })
        .expect("resolve")
}

fn targets(r: &Resolution) -> Vec<&str> {
    r.calls.iter().map(|c| c.entity.as_str()).collect()
}

fn executes(text: &str, expected: &[&str], action: &str) {
    let r = ask(text);
    assert_eq!(r.decision, Decision::Execute, "{text}: {r:?}");
    assert_eq!(targets(&r), expected, "{text}");
    assert!(r.calls.iter().all(|c| c.action == action), "{text}: {r:?}");
}

#[test]
fn bedroom_lights_in_many_wordings() {
    for text in [
        "accendi le luci della camera da letto",
        "accendi la luce della camera da letto",
        "accendimi le luci in camera da letto per favore",
        "camera da letto, accendi le luci",
        "Nuxiva puoi accendere le luci della camera da letto?",
        "luci camera da letto accese",
        "accendi luci camera letto",
        "ACCENDI LE LUCI DELLA CAMERA DA LETTO",
        "turn on the bedroom lights",
        "switch on the lights in the bedroom",
        "enciende las luces del dormitorio",
        "allume les lumières de la chambre",
        "accendi la camera da letto",
    ] {
        executes(text, BEDROOM, "on");
    }
}

#[test]
fn transcription_errors_are_tolerated() {
    for text in [
        "accendi le lucci della camera da leto",
        "acendi le luci della camera da letto",
        "spengi le luci della camera da letto",
    ] {
        let r = ask(text);
        assert!(
            matches!(r.decision, Decision::Execute | Decision::Confirm),
            "{text}: {r:?}"
        );
        assert_eq!(targets(&r), BEDROOM, "{text}");
    }
}

#[test]
fn switching_off_and_states() {
    executes("spegni le luci della camera da letto", BEDROOM, "off");
    executes("luci della camera da letto spente", BEDROOM, "off");
    executes(
        "turn off the kitchen lights",
        &["light.cucina", "light.led_cucina"],
        "off",
    );
}

#[test]
fn names_win_over_rooms() {
    executes("spegni la plafoniera", &["light.plafoniera"], "off");
    executes("accendi l'abat jour", &["light.abat_jour"], "on");
    executes("spegni la macchina del caffè", &["switch.caffe"], "off");
    executes("accendi il lampadario", &["light.lampadario"], "on");
    executes(
        "accendi la striscia led della cucina",
        &["light.led_cucina"],
        "on",
    );
    executes("accendi la tv", &["media_player.tv"], "on");
    executes("accendi il condizionatore", &["climate.studio"], "on");
    executes("spegni il ventilatore dello studio", &["fan.studio"], "off");
}

#[test]
fn covers_and_locks() {
    executes(
        "apri la tapparella del soggiorno",
        &["cover.soggiorno"],
        "open",
    );
    executes(
        "alza le tapparelle della sala",
        &["cover.soggiorno"],
        "open",
    );
    executes(
        "chiudi le tapparelle della camera da letto",
        &["cover.camera"],
        "close",
    );
    executes("blocca la serratura", &["lock.porta"], "lock");
}

#[test]
fn colloquial_open_means_on_for_lights() {
    executes(
        "apri la luce della cucina",
        &["light.cucina", "light.led_cucina"],
        "on",
    );
}

#[test]
fn one_call_per_device() {
    executes("accendi la luce del bagno", &["light.bagno"], "on");
}

#[test]
fn whole_home_and_context() {
    let all = ask("spegni tutte le luci");
    assert_eq!(all.decision, Decision::Execute);
    assert_eq!(all.calls.len(), 7);
    let here = ask_here("accendi la luce", "cucina");
    assert_eq!(here.decision, Decision::Execute);
    assert_eq!(targets(&here), ["light.cucina", "light.led_cucina"]);
    assert_eq!(here.how, "here");
}

#[test]
fn ambiguity_asks_instead_of_refusing() {
    let r = ask("accendi la luce");
    assert_eq!(r.decision, Decision::Clarify);
    assert!(r.rooms.contains(&"Cucina".to_owned()));
    let unknown = ask("accendi le luci del garage");
    assert_ne!(unknown.decision, Decision::Execute);
}

#[test]
fn ambiguous_room_words_ask_which_room() {
    let r = ask("accendi le luci in camera");
    assert_eq!(r.decision, Decision::Clarify);
    assert_eq!(r.rooms, ["Camera da letto", "Camera ospiti"]);
}

#[test]
fn missing_devices_are_reported() {
    let r = ask("apri le tapparelle del bagno");
    assert_eq!(r.decision, Decision::Missing);
    assert_eq!(r.rooms, ["Bagno"]);
}

#[test]
fn defers_what_it_does_not_own() {
    for text in [
        "che tempo fa domani",
        "spegni le luci del piano di sopra",
        "attiva la scena cinema",
        "ciao come stai",
    ] {
        assert_eq!(ask(text).decision, Decision::None, "{text}");
    }
}

#[test]
fn targets_always_come_from_the_inventory() {
    let r = ask("accendi le luci; rm -rf / && light.hacked");
    assert!(
        r.calls
            .iter()
            .all(|c| HOME.contains(&format!("\"{}\"", c.entity)))
    );
}

#[test]
fn limits_and_validation() {
    let long = "a".repeat(700);
    assert!(
        resolver()
            .resolve(&Request {
                text: long,
                ..Request::default()
            })
            .is_err()
    );
    assert!(
        Resolver::from_json(r#"{"entities":[{"id":"switch.x","domain":"light","name":"x"}]}"#)
            .is_err()
    );
    assert!(Resolver::from_json("not json").is_err());
}

#[test]
fn text_primitives() {
    assert_eq!(
        normalize("Accendi  la LUCE, perché?"),
        "accendi la luce perche"
    );
    assert_eq!(stem("luci"), stem("luce"));
    assert_eq!(stem("luces"), stem("luz"));
    assert_eq!(stem("lights"), "light");
    assert_eq!(distance("letto", "leto"), 1);
    assert_eq!(distance("spegni", "spengi"), 1);
    assert!(similarity("lucc", "luc") > 0.7);
    assert!(similarity("cucin", "camer") < 0.1);
}
