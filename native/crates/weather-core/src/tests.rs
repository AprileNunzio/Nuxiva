use super::*;
use insights::{Day, Hour, Slot};

fn forecast(model: &str, time: &str, temp: f64, rain: f64, wind: f64) -> Forecast {
    Forecast {
        model: model.into(),
        lead: 1,
        time: time.into(),
        temp: Some(temp),
        rain: Some(rain),
        wind: Some(wind),
    }
}

fn seen(time: &str, temp: f64, rain: f64, wind: f64) -> Observation {
    Observation {
        time: time.into(),
        temp: Some(temp),
        rain: Some(rain),
        wind: Some(wind),
    }
}

#[test]
fn closer_model_wins() {
    let truth = vec![seen("t1", 10.0, 0.0, 10.0), seen("t2", 12.0, 1.0, 12.0)];
    let list = vec![
        forecast("good", "t1", 10.5, 0.0, 11.0),
        forecast("good", "t2", 12.5, 0.8, 12.0),
        forecast("bad", "t1", 14.0, 2.0, 25.0),
        forecast("bad", "t2", 8.0, 0.0, 2.0),
        forecast("lost", "t9", 1.0, 0.0, 1.0),
    ];
    let verdict = verify(&list, &truth, None, 2);
    assert_eq!(verdict.best.as_deref(), Some("good"));
    assert_eq!(verdict.models.len(), 2);
    let good = verdict
        .models
        .first()
        .map(|m| (m.temp_mae, m.rain_accuracy, m.pairs));
    assert_eq!(good, Some((Some(0.5), Some(1.0), 2)));
}

#[test]
fn needs_enough_pairs_and_lead_filter() {
    let truth = vec![seen("t1", 10.0, 0.0, 10.0)];
    let mut far = forecast("far", "t1", 10.0, 0.0, 10.0);
    far.lead = 3;
    let verdict = verify(&[far.clone()], &truth, None, 5);
    assert_eq!(verdict.best, None);
    assert!(verify(&[far], &truth, Some(1), 1).models.is_empty());
}

#[test]
fn ignores_non_finite() {
    let truth = vec![Observation {
        time: "t".into(),
        temp: Some(f64::NAN),
        rain: None,
        wind: None,
    }];
    let verdict = verify(&[forecast("m", "t", 1.0, 0.0, 1.0)], &truth, None, 1);
    assert!(verdict.models.is_empty());
}

fn hour(time: &str, prob: f64, gust: f64, feels: f64, code: i64) -> Hour {
    Hour {
        time: time.into(),
        temp: Some(feels),
        feels: Some(feels),
        rain_prob: Some(prob),
        rain: Some(0.0),
        gust: Some(gust),
        uv: None,
        code: Some(code),
    }
}

#[test]
fn insights_cover_risks_sorted_by_level() {
    let situation = Situation {
        hourly: vec![
            hour("h0", 20.0, 30.0, 20.0, 2),
            hour("h1", 85.0, 80.0, 39.0, 95),
        ],
        days: vec![Day {
            tmax: Some(22.0),
            tmin: Some(0.0),
            uv: Some(7.0),
        }],
        yesterday: Some(Day {
            tmax: Some(18.5),
            tmin: None,
            uv: None,
        }),
        nowcast: vec![
            Slot {
                time: "n0".into(),
                rain: Some(0.0),
            },
            Slot {
                time: "n1".into(),
                rain: Some(0.4),
            },
        ],
    };
    let out = insights(&situation);
    let kinds: Vec<&str> = out.iter().map(|i| i.kind).collect();
    assert_eq!(
        kinds,
        [
            "storm",
            "wind",
            "heat",
            "rain_soon",
            "umbrella",
            "frost",
            "uv",
            "warmer"
        ]
    );
    assert_eq!(out.last().and_then(|i| i.value), Some(3.5));
}

#[test]
fn calm_day_has_only_comparison() {
    let situation = Situation {
        hourly: vec![hour("h0", 5.0, 10.0, 18.0, 1)],
        days: vec![Day {
            tmax: Some(18.0),
            tmin: Some(9.0),
            uv: Some(2.0),
        }],
        yesterday: Some(Day {
            tmax: Some(18.4),
            tmin: None,
            uv: None,
        }),
        nowcast: vec![],
    };
    let out = insights(&situation);
    assert_eq!(out.len(), 1);
    assert_eq!(out.first().map(|i| i.kind), Some("same"));
}

#[test]
fn rounding_is_half_up() {
    assert!((round_to(2.25, 1) - 2.3).abs() < 1e-9);
    assert!((round_to(-0.05, 1) - 0.0).abs() < 1e-9);
}
