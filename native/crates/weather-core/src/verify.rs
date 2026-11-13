use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::round_to;

pub const TEMP_SPAN: f64 = 5.0;
pub const WIND_SPAN: f64 = 20.0;
pub const WET_MM: f64 = 0.2;

#[derive(Debug, Clone, Deserialize)]
pub struct Forecast {
    pub model: String,
    pub lead: u32,
    pub time: String,
    pub temp: Option<f64>,
    pub rain: Option<f64>,
    pub wind: Option<f64>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Observation {
    pub time: String,
    pub temp: Option<f64>,
    pub rain: Option<f64>,
    pub wind: Option<f64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct ModelScore {
    pub model: String,
    pub pairs: u32,
    pub temp_mae: Option<f64>,
    pub temp_bias: Option<f64>,
    pub rain_accuracy: Option<f64>,
    pub wind_mae: Option<f64>,
    pub score: f64,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Verdict {
    pub models: Vec<ModelScore>,
    pub best: Option<String>,
}

#[derive(Default)]
struct Tally {
    pairs: u32,
    temp_n: u32,
    temp_abs: f64,
    temp_sum: f64,
    rain_n: u32,
    rain_hits: u32,
    wind_n: u32,
    wind_abs: f64,
}

fn finite(value: Option<f64>) -> Option<f64> {
    value.filter(|v| v.is_finite())
}

fn mean(total: f64, count: u32) -> Option<f64> {
    (count > 0).then(|| total / f64::from(count))
}

impl Tally {
    fn add(&mut self, forecast: &Forecast, seen: &Observation) {
        let mut used = false;
        if let (Some(f), Some(o)) = (finite(forecast.temp), finite(seen.temp)) {
            self.temp_n = self.temp_n.saturating_add(1);
            self.temp_abs += (f - o).abs();
            self.temp_sum += f - o;
            used = true;
        }
        if let (Some(f), Some(o)) = (finite(forecast.rain), finite(seen.rain)) {
            self.rain_n = self.rain_n.saturating_add(1);
            if (f >= WET_MM) == (o >= WET_MM) {
                self.rain_hits = self.rain_hits.saturating_add(1);
            }
            used = true;
        }
        if let (Some(f), Some(o)) = (finite(forecast.wind), finite(seen.wind)) {
            self.wind_n = self.wind_n.saturating_add(1);
            self.wind_abs += (f - o).abs();
            used = true;
        }
        if used {
            self.pairs = self.pairs.saturating_add(1);
        }
    }

    fn score(&self, model: String) -> ModelScore {
        let temp_mae = mean(self.temp_abs, self.temp_n);
        let temp_bias = mean(self.temp_sum, self.temp_n);
        let rain_accuracy =
            (self.rain_n > 0).then(|| f64::from(self.rain_hits) / f64::from(self.rain_n));
        let wind_mae = mean(self.wind_abs, self.wind_n);
        let mut weight = 0.0;
        let mut total = 0.0;
        if let Some(mae) = temp_mae {
            total += 0.5 * (1.0 - mae / TEMP_SPAN).max(0.0);
            weight += 0.5;
        }
        if let Some(accuracy) = rain_accuracy {
            total += 0.3 * accuracy;
            weight += 0.3;
        }
        if let Some(mae) = wind_mae {
            total += 0.2 * (1.0 - mae / WIND_SPAN).max(0.0);
            weight += 0.2;
        }
        let score = if weight > 0.0 { total / weight } else { 0.0 };
        ModelScore {
            model,
            pairs: self.pairs,
            temp_mae: temp_mae.map(|v| round_to(v, 3)),
            temp_bias: temp_bias.map(|v| round_to(v, 3)),
            rain_accuracy: rain_accuracy.map(|v| round_to(v, 4)),
            wind_mae: wind_mae.map(|v| round_to(v, 3)),
            score: round_to(score, 4),
        }
    }
}

#[must_use]
pub fn verify(
    forecasts: &[Forecast],
    observed: &[Observation],
    lead: Option<u32>,
    min_pairs: u32,
) -> Verdict {
    let truth: BTreeMap<&str, &Observation> =
        observed.iter().map(|o| (o.time.as_str(), o)).collect();
    let mut tallies: BTreeMap<&str, Tally> = BTreeMap::new();
    for forecast in forecasts {
        if lead.is_some_and(|wanted| wanted != forecast.lead) {
            continue;
        }
        if let Some(seen) = truth.get(forecast.time.as_str()) {
            tallies
                .entry(forecast.model.as_str())
                .or_default()
                .add(forecast, seen);
        }
    }
    let mut models: Vec<ModelScore> = tallies
        .into_iter()
        .filter(|(_, tally)| tally.pairs > 0)
        .map(|(name, tally)| tally.score(name.to_owned()))
        .collect();
    models.sort_by(|a, b| {
        b.score
            .total_cmp(&a.score)
            .then_with(|| b.pairs.cmp(&a.pairs))
            .then_with(|| a.model.cmp(&b.model))
    });
    let best = models
        .iter()
        .find(|m| m.pairs >= min_pairs.max(1))
        .map(|m| m.model.clone());
    Verdict { models, best }
}
