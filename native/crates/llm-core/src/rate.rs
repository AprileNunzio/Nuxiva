use regex::Regex;

const MAGNITUDE: f64 = 9.0e15;
const DEFAULT_COOLDOWN: f64 = 60.0;
const SERVER_COOLDOWN: f64 = 120.0;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ModelRate {
    pub remaining_requests: Option<i64>,
    pub request_limit: Option<i64>,
    pub remaining_tokens: Option<i64>,
    pub reset_at: f64,
    pub cooldown_until: f64,
    pub disabled: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Observed {
    Rate(ModelRate),
    Defer,
}

#[derive(Debug)]
pub struct RateRules {
    duration: Regex,
    plain: Regex,
}

fn printable(text: &str) -> bool {
    text.chars().all(|c| c == ' ' || c.is_ascii_graphic())
}

impl RateRules {
    pub fn new() -> Result<Self, regex::Error> {
        Ok(Self {
            duration: Regex::new(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([smhdSMHD]?)\s*$")?,
            plain: Regex::new(r"^[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")?,
        })
    }

    fn integer(&self, value: &str, minimum: i64) -> Result<Option<i64>, ()> {
        if !self.plain.is_match(value.trim()) {
            return Err(());
        }
        let parsed: f64 = value.trim().parse().map_err(|_| ())?;
        if !parsed.is_finite() {
            return Ok(None);
        }
        if parsed.abs() > MAGNITUDE {
            return Err(());
        }
        #[allow(clippy::cast_possible_truncation)]
        Ok(Some(minimum.max(parsed.trunc() as i64)))
    }

    fn reset_value(&self, value: &str, now: f64) -> Result<f64, ()> {
        let found = self.duration.captures(value).ok_or(())?;
        let number: f64 = found.get(1).ok_or(())?.as_str().parse().map_err(|_| ())?;
        let scale = match found
            .get(2)
            .map(|unit| unit.as_str().to_ascii_lowercase())
            .as_deref()
        {
            Some("m") => 60.0,
            Some("h") => 3600.0,
            Some("d") => 86_400.0,
            _ => 1.0,
        };
        Ok(now + number * scale)
    }

    #[must_use]
    pub fn observe(
        &self,
        previous: ModelRate,
        headers: &[(String, String)],
        status: i64,
        now: f64,
    ) -> Observed {
        match self.observe_inner(previous, headers, status, now) {
            Ok(rate) => Observed::Rate(rate),
            Err(()) => Observed::Defer,
        }
    }

    fn observe_inner(
        &self,
        previous: ModelRate,
        headers: &[(String, String)],
        status: i64,
        now: f64,
    ) -> Result<ModelRate, ()> {
        if !headers
            .iter()
            .all(|(key, value)| printable(key) && printable(value))
        {
            return Err(());
        }
        let mut normalized: Vec<(String, String)> = Vec::with_capacity(headers.len());
        for (key, value) in headers {
            let (key, value) = (key.to_ascii_lowercase(), value.trim().to_owned());
            match normalized.iter_mut().find(|(name, _)| *name == key) {
                Some(slot) => slot.1 = value,
                None => normalized.push((key, value)),
            }
        }
        let get = |name: &str| {
            normalized
                .iter()
                .find(|(key, _)| key == name)
                .map(|(_, value)| value.as_str())
        };
        let mut rate = previous;
        for (name, target) in [
            ("x-ratelimit-remaining-requests", 0),
            ("x-ratelimit-remaining-tokens", 1),
            ("x-ratelimit-remaining", 0),
        ] {
            if let Some(value) = get(name) {
                if let Some(parsed) = self.integer(value, 0)? {
                    if target == 0 {
                        rate.remaining_requests = Some(parsed);
                    } else {
                        rate.remaining_tokens = Some(parsed);
                    }
                }
            }
        }
        for name in ["x-ratelimit-limit-requests", "x-ratelimit-limit"] {
            if let Some(value) = get(name) {
                if let Some(parsed) = self.integer(value, 1)? {
                    rate.request_limit = Some(parsed);
                }
            }
        }
        let reset = [
            "retry-after",
            "x-ratelimit-reset-requests",
            "x-ratelimit-reset",
        ]
        .iter()
        .filter_map(|name| get(name))
        .find(|value| !value.is_empty());
        if let Some(value) = reset {
            rate.reset_at = self.reset_value(value, now)?;
        }
        if status == 429 {
            rate.cooldown_until = if rate.reset_at > now {
                rate.reset_at
            } else {
                now + DEFAULT_COOLDOWN
            };
        } else if status == 401 || status == 403 {
            rate.disabled = true;
        } else if status >= 500 {
            rate.cooldown_until = rate.cooldown_until.max(now + SERVER_COOLDOWN);
        }
        Ok(rate)
    }
}

#[must_use]
pub fn available(rate: &ModelRate, estimated_tokens: i64, now: f64) -> bool {
    if rate.disabled || rate.cooldown_until > now {
        return false;
    }
    if rate.remaining_requests.is_some_and(|left| left <= 1) && rate.reset_at > now {
        return false;
    }
    if rate
        .remaining_tokens
        .is_some_and(|left| left < estimated_tokens)
        && rate.reset_at > now
    {
        return false;
    }
    true
}
