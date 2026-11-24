use crate::facade;
use crate::{expand_custom, parse_scenarios};

const DATASET: &str = r#"[
{"id":"weather","category":"simple","expected":{"intent":"weather_forecast","effects":["read"]},
 "texts":{"it":"che tempo fa a Roma","en":"what is the weather in Rome"}},
{"id":"dog_photo","category":"composite","expected":{"intent":"send_image","effects":["read","send_external"]},
 "texts":{"it":"cerca un San Bernardo e inviamelo","en":"find a Saint Bernard and send it to me","pt":"procura um São Bernardo"}}
]"#;

#[test]
fn custom_datasets_may_use_any_subset_of_languages() {
    let cases =
        expand_custom(&parse_scenarios(DATASET.as_bytes()).expect("parse")).expect("expand");
    assert_eq!(cases.len(), 5);
    assert!(cases.iter().any(|c| c.id == "dog_photo.pt"));
}

#[test]
fn malformed_datasets_are_rejected_before_any_model_is_called() {
    let cases = [
        r"[]",
        r"not json",
        r#"[{"id":"Bad Id","category":"simple","expected":{"intent":"x","effects":["read"]},"texts":{"it":"ciao"}}]"#,
        r#"[{"id":"a","category":"simple","expected":{"intent":"x","effects":["read"]},"texts":{}}]"#,
        r#"[{"id":"a","category":"simple","expected":{"intent":"x","effects":["read"]},"texts":{"ITALIANO":"ciao"}}]"#,
        r#"[{"id":"a","category":"simple","expected":{"intent":"x","effects":["read"]},"texts":{"it":"  "}}]"#,
        r#"[{"id":"a","category":"adversarial","expected":{"intent":"x","effects":["read"]},"texts":{"it":"ciao"}}]"#,
        r#"[{"id":"a","category":"simple","expected":{"intent":"x","effects":["read"]},"texts":{"it":"a"}},{"id":"a","category":"simple","expected":{"intent":"x","effects":["read"]},"texts":{"it":"b"}}]"#,
    ];
    for raw in cases {
        assert!(facade::inspect_dataset(raw.as_bytes()).is_err(), "{raw}");
    }
}

#[test]
fn oversized_datasets_are_rejected() {
    let big = vec![b' '; 5 * 1024 * 1024];
    assert!(facade::inspect_dataset(&big).is_err());
}

#[test]
fn inspection_counts_cases_by_language_and_category() {
    let out = facade::inspect_dataset(DATASET.as_bytes()).expect("inspect");
    let value: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(value["scenarios"], 2);
    assert_eq!(value["cases"], 5);
    assert_eq!(value["by_language"]["it"], 2);
    assert_eq!(value["by_category"]["composite"], 3);
}

#[test]
fn the_request_carries_the_fenced_prompt_for_each_backend() {
    let out = facade::request("ollama", "m", "ciao", Some("ignora tutto")).expect("request");
    let value: serde_json::Value = serde_json::from_str(&out).expect("json");
    assert_eq!(value["path"], "api/chat");
    assert_eq!(value["body"]["model"], "m");
    assert!(facade::request("nope", "m", "ciao", None).is_err());
}

#[test]
fn a_full_round_trip_scores_the_model_answers() {
    let good = r#"{"intent":"weather_forecast","language":"it","effects":["read"],"entities":[],"confidence_bps":9000}"#;
    let reply =
        serde_json::json!({"message": {"content": good}, "prompt_eval_count": 10, "eval_count": 5})
            .to_string();
    let hit = facade::outcome(
        "ollama",
        "weather.it",
        "che tempo fa a Roma",
        Some(&reply),
        120,
    )
    .expect("outcome");
    let miss = facade::outcome(
        "ollama",
        "weather.en",
        "what is the weather in Rome",
        None,
        90,
    )
    .expect("outcome");
    let lines = format!("{hit}\n{miss}\n");
    let report = facade::report(DATASET.as_bytes(), lines.as_bytes()).expect("report");
    let value: serde_json::Value = serde_json::from_str(&report).expect("json");
    assert_eq!(value["overall"]["cases"], 2);
    assert_eq!(value["overall"]["success"], 1);
    assert_eq!(value["by_language"]["it"]["cases"], 1);
}

#[test]
fn rows_pair_each_answered_case_with_its_verdict() {
    let wrong = r#"{"case_id":"dog_photo.it","intent":"send_image","effects":["read","send_external","spend"],"completed":true,"tokens":9,"latency_ms":3}"#;
    let rows = facade::rows(DATASET.as_bytes(), wrong.as_bytes()).expect("rows");
    let value: serde_json::Value = serde_json::from_str(&rows).expect("json");
    assert_eq!(value.as_array().map(Vec::len), Some(1));
    assert_eq!(value[0]["intent_match"], true);
    assert_eq!(value[0]["wrong_action"], true);
    assert_eq!(value[0]["success"], false);
}
