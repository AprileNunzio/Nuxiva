use capability_registry::Role;
use reason_exec::{Journal, Record, step_key};
use serde_json::json;

use crate::{Config, DAY_MS, Engine, Ledger, Mode, Prepared, Sample, SealedJournal, Verdict, line};

const USER: &str = "cerca il meteo di Roma";

fn document() -> String {
    let weather = json!({"id":"weather.forecast","version":1,"origin":"local","summary":"Previsioni meteo per una città","inputs":[{"name":"city","ty":"text","required":true}],"output":"text","effects":["read"],"reversible":true,"min_role":"guest","nodes":["server"]});
    let mail = json!({"id":"email.send","version":1,"origin":"local","summary":"Invia una email","inputs":[{"name":"to","ty":"contact","required":true},{"name":"body","ty":"text","required":true}],"output":"text","effects":["send_external"],"reversible":false,"min_role":"family","nodes":["server"]});
    let lamp = json!({"id":"home.light","version":1,"origin":"local","summary":"Accende una luce","inputs":[],"output":"text","effects":["physical"],"reversible":true,"min_role":"family","nodes":["server"]});
    json!({"schema":1,"capabilities":[weather, mail, lamp]}).to_string()
}

fn raw_goal() -> String {
    json!({"intent":"get_weather_forecast","language":"it","effects":["read"],"entities":[{"role":"city","ty":"text","value":"Roma","source":"user"}],"confidence_bps":9300}).to_string()
}

fn engine() -> Engine {
    let mut engine = Engine::new(Config::default());
    assert_eq!(
        engine
            .load_registry(document().as_bytes())
            .expect("registry"),
        3
    );
    engine
}

fn good_plan() -> String {
    json!({"steps":[{"id":"forecast","capability":"weather.forecast","args":{"city":{"from":"entity","role":"city"}}}]}).to_string()
}

#[test]
fn prompt_lists_only_permitted_capabilities_without_user_values() {
    let mut engine = engine();
    let goal = Engine::goal(&raw_goal(), USER).expect("goal");
    let Prepared::Ask(request) = engine.prepare(&goal, USER, Role::Guest, 0) else {
        panic!("expected a prompt");
    };
    assert!(
        request
            .capabilities
            .contains(&"weather.forecast".to_owned())
    );
    assert!(!request.capabilities.contains(&"email.send".to_owned()));
    assert!(!request.user.contains("Roma"));
    assert!(
        request
            .user
            .contains("weather.forecast(city:text) -> text [read]")
    );
}

#[test]
fn valid_plan_is_accepted_cached_and_reused() {
    let mut engine = engine();
    let goal = Engine::goal(&raw_goal(), USER).expect("goal");
    let Prepared::Ask(request) = engine.prepare(&goal, USER, Role::Guest, 0) else {
        panic!("expected a prompt");
    };
    let Verdict::Accepted(checked) = engine.accept(
        &goal,
        USER,
        Role::Guest,
        &good_plan(),
        &request.capabilities,
        0,
    ) else {
        panic!("expected acceptance");
    };
    assert!(checked.executable());
    engine.remember(&goal, &checked, 10);
    let Prepared::Cached(again) = engine.prepare(&goal, "che tempo fa a Roma", Role::Guest, 20)
    else {
        panic!("expected cache");
    };
    assert!(again.cached);
    assert_eq!(again.hash, checked.hash);
    assert_eq!(engine.cache_stats().1, 1);
    let Prepared::Ask(_) = engine.prepare(&goal, USER, Role::Guest, 20 + DAY_MS) else {
        panic!("expired entry must not be reused");
    };
}

#[test]
fn unlisted_capability_gets_one_correction_then_rejection() {
    let engine = engine();
    let goal = Engine::goal(&raw_goal(), USER).expect("goal");
    let request = crate::build(&goal, &[], None);
    let bad = json!({"steps":[{"id":"a","capability":"home.light"}]}).to_string();
    let Verdict::Retry {
        code,
        request: retry,
    } = engine.accept(&goal, USER, Role::Guest, &bad, &request.capabilities, 0)
    else {
        panic!("expected retry");
    };
    assert_eq!(code, "plan.unlisted_capability.home.light");
    assert!(retry.user.contains("PREVIOUS PLAN REJECTED"));
    let Verdict::Rejected(_) =
        engine.accept(&goal, USER, Role::Guest, &bad, &retry.capabilities, 1)
    else {
        panic!("expected rejection");
    };
}

#[test]
fn shadow_comparison_matches_legacy_tools() {
    let plan = reason_plan::parse(&good_plan()).expect("plan");
    assert!(Engine::compare(&plan, &["weather.forecast"]).matches());
    assert!(!Engine::compare(&plan, &["connector.music"]).matches());
}

#[test]
fn gate_opens_only_after_days_samples_and_agreement() {
    let mut engine = engine();
    let good = Sample {
        comparable: true,
        agreed: true,
        valid: true,
        ..Sample::default()
    };
    for day in 0..7u64 {
        for _ in 0..30 {
            engine.record(&good, day * DAY_MS);
        }
    }
    let now = 6 * DAY_MS;
    assert!(engine.status(now).ready, "{:?}", engine.status(now).reasons);
    assert_eq!(engine.set_mode(Mode::Active, false, now), Ok(Mode::Active));
    engine.kill();
    assert_eq!(engine.mode().mode, Mode::Off);
    engine.record(
        &Sample {
            wrong_action: true,
            ..good
        },
        now,
    );
    let status = engine.status(now);
    assert!(!status.ready);
    assert!(status.reasons.contains(&"reason.gate.wrong_actions"));
    assert!(engine.set_mode(Mode::Active, false, now).is_err());
    assert_eq!(engine.set_mode(Mode::Active, true, now), Ok(Mode::Active));
    assert!(engine.mode().forced);
}

#[test]
fn ledger_round_trips_and_drops_old_days() {
    let mut ledger = Ledger::default();
    ledger.record(&Sample::default(), 0);
    ledger.record(&Sample::default(), 100 * DAY_MS);
    let parsed = Ledger::parse(&ledger.to_json().expect("json")).expect("parse");
    assert_eq!(parsed, ledger);
    let status = parsed.status(&crate::Gate::default(), 100 * DAY_MS);
    assert_eq!(status.totals.total, 1);
    assert!(Ledger::parse("{\"days\":{\"1\":{\"bogus\":1}}}").is_err());
}

#[test]
fn config_rejects_out_of_range_values() {
    assert!(Config::parse("{\"retrieve_limit\":0}").is_err());
    assert!(Config::parse("{\"gate\":{\"min_agreement_bps\":20000}}").is_err());
    let parsed = Config::parse("{\"retrieve_limit\":6,\"gate\":{\"min_days\":3}}").expect("config");
    assert_eq!(parsed.retrieve_limit, 6);
    assert_eq!(parsed.gate.min_days, 3);
    assert_eq!(parsed.gate.min_samples, 200);
}

#[test]
fn sealed_journal_survives_restart_and_detects_tampering() {
    let dir = std::env::temp_dir().join(format!("reason-journal-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("dir");
    let path = dir.join("journal.log");
    let _ = std::fs::remove_file(&path);
    let key = step_key("plan", "send", &std::collections::BTreeMap::new());
    {
        let mut journal = SealedJournal::open(&path, [7; 32], 64).expect("open");
        journal.append(&key, Record::Started).expect("started");
        journal
            .append(&key, Record::Succeeded("segreto".into()))
            .expect("done");
    }
    let raw = std::fs::read_to_string(&path).expect("read");
    assert!(!raw.contains("segreto"));
    let reopened = SealedJournal::open(&path, [7; 32], 64).expect("reopen");
    assert_eq!(
        reopened.last(&key),
        Some(&Record::Succeeded("segreto".into()))
    );
    assert!(SealedJournal::open(&path, [8; 32], 64).is_err());
    assert!(
        SealedJournal::open(&path, [7; 32], 64)
            .expect("open")
            .append("short", Record::Started)
            .is_err()
    );
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn journal_compacts_when_full() {
    let dir = std::env::temp_dir().join(format!("reason-compact-{}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("dir");
    let path = dir.join("journal.log");
    let _ = std::fs::remove_file(&path);
    let key = step_key("plan", "a", &std::collections::BTreeMap::new());
    let mut journal = SealedJournal::open(&path, [1; 32], 16).expect("open");
    for _ in 0..40 {
        journal.append(&key, Record::Started).expect("append");
    }
    assert_eq!(journal.keys(), 1);
    let lines = std::fs::read_to_string(&path)
        .expect("read")
        .lines()
        .count();
    assert!(lines <= 16);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn catalogue_line_marks_optional_inputs() {
    let doc: serde_json::Value = serde_json::from_str(&document()).expect("doc");
    let contract: capability_registry::Contract =
        serde_json::from_value(doc["capabilities"][1].clone()).expect("contract");
    assert_eq!(
        line(&contract),
        "- email.send(to:contact, body:text) -> text [send_external]: Invia una email"
    );
}
