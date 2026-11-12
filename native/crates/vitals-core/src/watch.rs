use std::collections::BTreeMap;

pub const ATTEMPT: f64 = 60.0;
pub const RETRY_FIRST: f64 = 20.0;
pub const RETRY_MAX: f64 = 300.0;
pub const SHOW: f64 = 45.0;
pub const REFRESH: f64 = 15.0 * 60.0;
pub const AWAY_GRACE: f64 = 8.0;
pub const FORGET_AFTER: f64 = 30.0 * 60.0;
pub const MAX_PEOPLE: usize = 4;
pub const MAX_TRACKED: usize = 64;
pub const HEART_LIMITS: (f64, f64) = (40.0, 180.0);
pub const BREATH_LIMITS: (f64, f64) = (5.0, 40.0);
const MAX_SLUG: usize = 64;
const RESTRICTED_ROLES: [&str; 2] = ["guest", "service"];

#[must_use]
pub fn valid_slug(slug: &str) -> bool {
    let bytes = slug.as_bytes();
    let tail_ok = |b: &u8| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'_' || *b == b'-';
    match bytes.first() {
        Some(first) if bytes.len() <= MAX_SLUG => {
            (first.is_ascii_lowercase() || first.is_ascii_digit()) && bytes.iter().all(tail_ok)
        }
        _ => false,
    }
}

#[must_use]
pub fn camera_allowed(
    consent: Option<bool>,
    camera_vitals: Option<bool>,
    role: &str,
    share_health: Option<bool>,
) -> bool {
    if consent == Some(false) || camera_vitals == Some(false) {
        return false;
    }
    if RESTRICTED_ROLES.contains(&role) {
        return share_health == Some(true);
    }
    true
}

fn clean(value: Option<f64>, (low, high): (f64, f64)) -> Option<f64> {
    value
        .filter(|v| v.is_finite() && *v >= low && *v <= high)
        .map(f64::round_ties_even)
}

#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct Values {
    pub heart: Option<f64>,
    pub breath: Option<f64>,
}

impl Values {
    #[must_use]
    pub fn cleaned(heart: Option<f64>, breath: Option<f64>) -> Self {
        Self {
            heart: clean(heart, HEART_LIMITS),
            breath: clean(breath, BREATH_LIMITS),
        }
    }

    fn merge(&mut self, other: Self) {
        self.heart = other.heart.or(self.heart);
        self.breath = other.breath.or(self.breath);
    }

    fn any(self) -> bool {
        self.heart.is_some() || self.breath.is_some()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Source {
    #[default]
    None,
    Device,
    Camera,
}

impl Source {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::None => "",
            Self::Device => "device",
            Self::Camera => "camera",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum State {
    Idle,
    Attempt,
    Rest,
    Shown,
    Cooldown,
}

#[derive(Debug, Clone)]
struct Person {
    state: State,
    since: f64,
    tries: u32,
    values: Values,
    source: Source,
    got_at: f64,
    last_seen: f64,
}

impl Person {
    fn new(now: f64) -> Self {
        Self {
            state: State::Idle,
            since: now,
            tries: 0,
            values: Values::default(),
            source: Source::None,
            got_at: 0.0,
            last_seen: now,
        }
    }

    fn reset(&mut self, now: f64) {
        *self = Self {
            last_seen: self.last_seen,
            ..Self::new(now)
        };
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Seen {
    pub slug: String,
    pub device: Values,
    pub camera: Values,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Shown {
    pub slug: String,
    pub values: Values,
    pub source: Source,
    pub at: f64,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Outcome {
    pub shown: Vec<Shown>,
    pub force: Vec<(String, f64)>,
}

#[derive(Debug, Default)]
pub struct Watch {
    people: BTreeMap<String, Person>,
}

fn gap(tries: u32) -> f64 {
    let exponent = i32::try_from(tries.saturating_sub(1).min(8)).unwrap_or(8);
    (RETRY_FIRST * 2f64.powi(exponent)).min(RETRY_MAX)
}

impl Watch {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn tracked(&self) -> usize {
        self.people.len()
    }

    fn show(person: &mut Person, values: Values, source: Source, now: f64) {
        if person.state != State::Shown {
            person.state = State::Shown;
            person.since = now;
            person.tries = 0;
            person.values = Values::default();
        }
        person.values.merge(values);
        person.source = source;
        person.got_at = now;
    }

    fn step(
        slug: &str,
        person: &mut Person,
        seen: &Seen,
        camera_on: bool,
        now: f64,
        force: &mut Vec<(String, f64)>,
    ) {
        if person.state == State::Shown && now - person.since >= SHOW {
            force.push((slug.to_owned(), 0.0));
            person.state = State::Cooldown;
            person.since = now;
            return;
        }
        if person.state != State::Cooldown && seen.device.heart.is_some() {
            if person.state == State::Attempt {
                force.push((slug.to_owned(), 0.0));
            }
            Self::show(person, seen.device, Source::Device, now);
            return;
        }
        match person.state {
            State::Idle => {
                person.state = State::Attempt;
                person.since = now;
                if camera_on {
                    force.push((slug.to_owned(), ATTEMPT));
                }
            }
            State::Attempt => {
                if seen.camera.heart.is_some() {
                    Self::show(person, seen.camera, Source::Camera, now);
                } else if now - person.since >= ATTEMPT || !camera_on {
                    force.push((slug.to_owned(), 0.0));
                    person.tries = person.tries.saturating_add(1);
                    person.state = State::Rest;
                    person.since = now;
                }
            }
            State::Rest => {
                if now - person.since >= gap(person.tries) {
                    person.state = State::Attempt;
                    person.since = now;
                    if camera_on {
                        force.push((slug.to_owned(), ATTEMPT));
                    }
                }
            }
            State::Shown => {
                if person.source == Source::Camera && seen.camera.any() {
                    Self::show(person, seen.camera, Source::Camera, now);
                }
            }
            State::Cooldown => {
                if now - person.since >= REFRESH {
                    person.reset(now);
                }
            }
        }
    }

    fn leave(slug: &str, person: &mut Person, now: f64, force: &mut Vec<(String, f64)>) {
        match person.state {
            State::Attempt | State::Shown => force.push((slug.to_owned(), 0.0)),
            _ => {}
        }
        match person.state {
            State::Shown => {
                person.state = State::Cooldown;
                person.since = now;
            }
            State::Cooldown => {}
            _ => person.reset(now),
        }
    }

    pub fn tick(&mut self, seen: &[Seen], camera_on: bool, now: f64) -> Outcome {
        let mut out = Outcome::default();
        if !now.is_finite() {
            return out;
        }
        let mut present: Vec<&Seen> = Vec::with_capacity(MAX_PEOPLE);
        for s in seen {
            if present.len() >= MAX_PEOPLE {
                break;
            }
            if valid_slug(&s.slug) && !present.iter().any(|p| p.slug == s.slug) {
                present.push(s);
            }
        }
        for s in &present {
            if !self.people.contains_key(&s.slug) && self.people.len() >= MAX_TRACKED {
                continue;
            }
            let person = self
                .people
                .entry(s.slug.clone())
                .or_insert_with(|| Person::new(now));
            person.last_seen = now;
            Self::step(&s.slug, person, s, camera_on, now, &mut out.force);
        }
        let mut gone = Vec::new();
        for (slug, person) in &mut self.people {
            if present.iter().any(|p| &p.slug == slug) {
                continue;
            }
            let away = now - person.last_seen;
            if away > FORGET_AFTER {
                out.force.push((slug.clone(), 0.0));
                gone.push(slug.clone());
            } else if away > AWAY_GRACE {
                Self::leave(slug, person, now, &mut out.force);
            }
        }
        for slug in gone {
            self.people.remove(&slug);
        }
        out.shown = present
            .iter()
            .filter_map(|s| {
                let person = self.people.get(&s.slug)?;
                (person.state == State::Shown).then(|| Shown {
                    slug: s.slug.clone(),
                    values: person.values,
                    source: person.source,
                    at: person.got_at,
                })
            })
            .collect();
        out
    }

    pub fn forget(&mut self, slug: &str) -> bool {
        self.people.remove(slug).is_some()
    }
}
