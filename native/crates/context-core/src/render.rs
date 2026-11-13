use crate::id::PersonId;
use crate::lexicon::{Labels, Lang};
use crate::model::{Affect, Person, Role};
use crate::policy::FieldKey;
use crate::seal::Sealer;
use crate::settings::ContextSettings;
use crate::snapshot::Snapshot;

#[derive(Debug, Clone)]
pub struct Request {
    pub subjects: Vec<PersonId>,
    pub present: Vec<PersonId>,
    pub lang: Lang,
    pub budget_chars: usize,
    pub now_ms: u64,
}

impl Request {
    #[must_use]
    pub fn cache_key(&self, bucket_ms: u64) -> String {
        let join = |ids: &[PersonId]| {
            ids.iter()
                .map(PersonId::as_str)
                .collect::<Vec<_>>()
                .join(",")
        };
        let mut present = self.present.clone();
        present.sort();
        format!(
            "{}|{}|{}|{}|{}",
            self.lang.code(),
            self.budget_chars,
            self.now_ms.checked_div(bucket_ms.max(1)).unwrap_or(0),
            join(&self.subjects),
            join(&present)
        )
    }
}

struct Piece {
    person: usize,
    priority: u8,
    text: String,
    keep: bool,
}

fn list_piece(label: &str, items: &[String]) -> Option<String> {
    (!items.is_empty()).then(|| format!("{label}: {}", items.join(", ")))
}

fn effective(affect: &Affect, now_ms: u64, settings: &ContextSettings) -> Option<(i16, u16)> {
    let age = now_ms.saturating_sub(affect.at_ms);
    if age > settings.affect_max_age_ms {
        return None;
    }
    let halvings = age
        .checked_div(settings.affect_half_life_ms.max(1))
        .unwrap_or(0)
        .min(15);
    let shift = u32::try_from(halvings).unwrap_or(15);
    Some((affect.valence >> shift, affect.arousal >> shift))
}

fn mood_piece(
    affect: &Affect,
    now_ms: u64,
    labels: &Labels,
    settings: &ContextSettings,
) -> Option<String> {
    let (valence, arousal) = effective(affect, now_ms, settings)?;
    let tone = match valence {
        v if v >= 300 => labels.mood_positive,
        v if v <= -300 => labels.mood_negative,
        _ => labels.mood_neutral,
    };
    let energy = match arousal {
        a if a >= 600 => format!(", {}", labels.energetic),
        a if a <= 250 => format!(", {}", labels.calm),
        _ => String::new(),
    };
    Some(format!("{}: {tone}{energy}", labels.mood))
}

fn identity_piece(person: &Person, labels: &Labels) -> String {
    let role = match person.role {
        Role::Family => labels.family,
        Role::Guest => labels.guest,
    };
    let mut out = format!("{} ({role})", person.name);
    if let Some(nick) = &person.nickname {
        out.push_str(", ");
        out.push_str(labels.call);
        out.push(' ');
        out.push_str(nick);
    }
    if let Some(age) = person.age {
        out.push_str(", ");
        out.push_str(&age.to_string());
        out.push(' ');
        out.push_str(labels.years);
    }
    out
}

fn relations_piece(person: &Person, snapshot: &Snapshot, labels: &Labels) -> Option<String> {
    let parts: Vec<String> = person
        .relations
        .iter()
        .filter_map(|r| {
            let other = snapshot.person(&r.with)?;
            other.consent.then(|| format!("{} {}", r.kind, other.name))
        })
        .collect();
    (!parts.is_empty()).then(|| format!("{}: {}", labels.relations, parts.join(", ")))
}

fn listening_piece(person: &Person, labels: &Labels) -> Option<String> {
    let parts: Vec<String> = person
        .listening
        .iter()
        .take(5)
        .map(|l| format!("{} - {}", l.title, l.artist))
        .collect();
    (!parts.is_empty()).then(|| format!("{}: {}", labels.listening, parts.join("; ")))
}

struct Ctx<'a> {
    snapshot: &'a Snapshot,
    settings: &'a ContextSettings,
    sealer: &'a Sealer,
    labels: &'static Labels,
    now_ms: u64,
}

struct Sink<'a> {
    index: usize,
    ctx: &'a Ctx<'a>,
    subject: &'a Person,
    others: &'a [Option<&'a Person>],
    out: Vec<Piece>,
}

impl Sink<'_> {
    fn allowed(&self, key: FieldKey) -> bool {
        self.ctx
            .settings
            .policy
            .allows(key, self.subject, self.others)
    }

    fn push(&mut self, priority: u8, key: FieldKey, text: Option<String>) {
        if let Some(text) = text {
            self.out.push(Piece {
                person: self.index,
                priority,
                text,
                keep: self.ctx.settings.policy.is_safety(key),
            });
        }
    }

    fn push_allowed(&mut self, priority: u8, key: FieldKey, text: impl FnOnce() -> Option<String>) {
        if self.allowed(key) {
            self.push(priority, key, text());
        }
    }

    fn vitals(&mut self) {
        let Some(sealed) = &self.subject.vitals else {
            return;
        };
        if !(self.allowed(FieldKey::Allergies) || self.allowed(FieldKey::Diet)) {
            return;
        }
        let Ok(vitals) = self.ctx.sealer.open(sealed) else {
            return;
        };
        let labels = self.ctx.labels;
        self.push_allowed(1, FieldKey::Allergies, || {
            list_piece(labels.allergies, &vitals.allergies)
        });
        self.push_allowed(1, FieldKey::Diet, || {
            vitals
                .diet
                .as_ref()
                .map(|d| format!("{}: {d}", labels.diet))
        });
    }

    fn lists(&mut self) {
        let labels = self.ctx.labels;
        let prefs = &self.subject.prefs;
        let lists: [(u8, FieldKey, &str, &[String]); 7] = [
            (6, FieldKey::Food, labels.food_likes, &prefs.food_likes),
            (
                6,
                FieldKey::Food,
                labels.food_dislikes,
                &prefs.food_dislikes,
            ),
            (7, FieldKey::Drinks, labels.drinks, &prefs.drinks),
            (8, FieldKey::Music, labels.music, &prefs.music),
            (9, FieldKey::Movies, labels.movies, &prefs.movies),
            (10, FieldKey::Sports, labels.sports, &prefs.sports),
            (11, FieldKey::Hobbies, labels.hobbies, &prefs.hobbies),
        ];
        for (priority, key, label, items) in lists {
            self.push_allowed(priority, key, || list_piece(label, items));
        }
    }

    fn rest(&mut self) {
        let ctx = self.ctx;
        let labels = ctx.labels;
        let person = self.subject;
        self.push_allowed(2, FieldKey::Today, || {
            list_piece(labels.today, &person.today)
        });
        self.push_allowed(3, FieldKey::Mood, || {
            person
                .affect
                .as_ref()
                .and_then(|a| mood_piece(a, ctx.now_ms, labels, ctx.settings))
        });
        self.push_allowed(4, FieldKey::Relations, || {
            relations_piece(person, ctx.snapshot, labels)
        });
        self.push_allowed(5, FieldKey::Work, || {
            person
                .work
                .as_ref()
                .map(|w| format!("{}: {w}", labels.work))
        });
        self.push_allowed(12, FieldKey::Custom, || {
            let custom: Vec<String> = person
                .prefs
                .custom
                .iter()
                .map(|c| format!("{}: {}", c.key, c.value))
                .collect();
            (!custom.is_empty()).then(|| custom.join("; "))
        });
        self.push_allowed(13, FieldKey::Listening, || listening_piece(person, labels));
    }
}

fn person_pieces<'a>(
    index: usize,
    person: &'a Person,
    others: &'a [Option<&'a Person>],
    ctx: &'a Ctx<'a>,
) -> Vec<Piece> {
    let mut sink = Sink {
        index,
        ctx,
        subject: person,
        others,
        out: Vec::new(),
    };
    if !sink.allowed(FieldKey::Identity) {
        return sink.out;
    }
    sink.push(
        0,
        FieldKey::Identity,
        Some(identity_piece(person, ctx.labels)),
    );
    sink.vitals();
    sink.lists();
    sink.rest();
    sink.out
}

fn total_chars(pieces: &[Piece]) -> usize {
    pieces
        .iter()
        .map(|p| p.text.chars().count().saturating_add(2))
        .fold(0_usize, usize::saturating_add)
}

fn fit(pieces: &mut Vec<Piece>, budget: usize) {
    while total_chars(pieces) > budget {
        let victim = pieces
            .iter()
            .enumerate()
            .filter(|(_, p)| !p.keep && p.priority > 0)
            .max_by_key(|(i, p)| (p.priority, p.person, *i))
            .map(|(i, _)| i);
        let Some(index) = victim else { break };
        pieces.remove(index);
    }
}

#[must_use]
pub fn render(
    snapshot: &Snapshot,
    request: &Request,
    settings: &ContextSettings,
    sealer: &Sealer,
) -> String {
    let budget = match request.budget_chars {
        0 => settings.default_budget_chars,
        n => n.min(settings.max_budget_chars),
    };
    let present: Vec<Option<&Person>> = request
        .present
        .iter()
        .map(|id| snapshot.person(id).map(|p| &**p))
        .collect();
    let ctx = Ctx {
        snapshot,
        settings,
        sealer,
        labels: request.lang.labels(),
        now_ms: request.now_ms,
    };
    let mut subjects: Vec<&PersonId> = Vec::new();
    for id in &request.subjects {
        if !subjects.contains(&id) {
            subjects.push(id);
        }
    }
    let mut pieces: Vec<Piece> = Vec::new();
    let mut count = 0_usize;
    for id in subjects {
        let Some(person) = snapshot.person(id) else {
            continue;
        };
        let others: Vec<Option<&Person>> = request
            .present
            .iter()
            .zip(&present)
            .filter(|(pid, _)| *pid != id)
            .map(|(_, p)| *p)
            .collect();
        pieces.extend(person_pieces(count, person, &others, &ctx));
        count = count.saturating_add(1);
    }
    fit(&mut pieces, budget);
    let mut lines: Vec<String> = Vec::with_capacity(count);
    for index in 0..count {
        let mut own: Vec<&Piece> = pieces.iter().filter(|p| p.person == index).collect();
        own.sort_by_key(|p| p.priority);
        if !own.is_empty() {
            lines.push(
                own.iter()
                    .map(|p| p.text.as_str())
                    .collect::<Vec<_>>()
                    .join(". "),
            );
        }
    }
    lines.join("\n")
}
