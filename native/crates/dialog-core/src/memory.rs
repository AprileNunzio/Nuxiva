use std::collections::{HashMap, VecDeque};

use regex::{NoExpand, Regex};

pub const KEEP: usize = 10;
pub const STALE_S: f64 = 15.0 * 60.0;
pub const MAX_DEVICES: usize = 256;
pub const MAX_DEVICE: usize = 128;
const TEXT_CHARS: usize = 400;
const REPLY_CHARS: usize = 600;
const WHO_CHARS: usize = 60;
const INTENT_CHARS: usize = 60;
const CONTEXT_TURNS: usize = 6;
const CONTEXT_REPLY: usize = 300;
const RESUME_TURNS: usize = 4;
const QUESTION_S: f64 = 60.0;
const NO_REPLY: f64 = 1e9;
const PUNCT: [char; 4] = [' ', '?', '!', '.'];

const ELLIPSIS: &str = r"(?i)^\s*(?:e|ed|invece|anche|mentre)\s+(?P<rest>.{1,60}?)\s*\??\s*$";
const TIME_WORDS: &str = r"(?i)\b(?:oggi|domani|dopodomani|stasera|stanotte|stamattina|ieri|questa settimana|(?:questo |il prossimo )?weekend|fine settimana|luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica|tra \d+ giorni|la prossima settimana)\b";
const PLACE: &str = r"\b(?:a|ad|in|per|da|su)\s+([A-ZÀ-Ý][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'-]+)?)";
const RESUME: &str = r"(?i)\b(?:dove eravamo(?: rimasti)?|come dicevamo|come stavamo dicendo|riprendiamo|ricominciamo da dove|tornando a(?: prima| quello)?|di cosa (?:stavamo parlando|parlavamo)|continuiamo (?:il discorso|da prima)|il discorso di prima)\b";
const SKILL_INTENTS: [&str; 10] = [
    "weather",
    "gservices",
    "maps",
    "place",
    "home",
    "action",
    "system",
    "network",
    "time",
    "music",
];

#[derive(Debug, Clone, PartialEq)]
pub struct Turn {
    pub text: String,
    pub reply: String,
    pub intent: String,
    pub at: f64,
    pub who: String,
}

impl Turn {
    #[must_use]
    pub fn new(text: &str, reply: &str, intent: &str, at: f64, who: &str) -> Self {
        Self {
            text: clip(text, TEXT_CHARS),
            reply: clip(reply, REPLY_CHARS),
            intent: clip(intent, INTENT_CHARS),
            at: if at.is_finite() { at } else { 0.0 },
            who: clip(who.trim(), WHO_CHARS),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Windows {
    pub stale: f64,
    pub resume: f64,
    pub recall: f64,
}

impl Default for Windows {
    fn default() -> Self {
        Self {
            stale: STALE_S,
            resume: 6.0 * 3600.0,
            recall: 24.0 * 3600.0,
        }
    }
}

impl Windows {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let pick =
            |v: f64, lo: f64, hi: f64, d: f64| if v.is_finite() { v.clamp(lo, hi) } else { d };
        let base = Self::default();
        let stale = pick(self.stale, 60.0, 86_400.0, base.stale);
        let resume = pick(self.resume, stale, 7.0 * 86_400.0, base.resume).max(stale);
        let recall = pick(self.recall, resume, 7.0 * 86_400.0, base.recall).max(resume);
        Self {
            stale,
            resume,
            recall,
        }
    }
}

fn clip(text: &str, chars: usize) -> String {
    text.chars().take(chars).collect()
}

#[derive(Debug, Clone)]
struct Patterns {
    ellipsis: Regex,
    time: Regex,
    place: Regex,
    resume: Regex,
}

impl Patterns {
    fn new() -> Result<Self, regex::Error> {
        Ok(Self {
            ellipsis: Regex::new(ELLIPSIS)?,
            time: Regex::new(TIME_WORDS)?,
            place: Regex::new(PLACE)?,
            resume: Regex::new(RESUME)?,
        })
    }
}

#[derive(Debug, Clone)]
pub struct DialogueBook {
    threads: HashMap<String, VecDeque<Turn>>,
    windows: Windows,
    patterns: Patterns,
}

impl DialogueBook {
    pub fn new(windows: Windows) -> Result<Self, regex::Error> {
        Ok(Self {
            threads: HashMap::new(),
            windows: windows.sanitized(),
            patterns: Patterns::new()?,
        })
    }

    #[must_use]
    pub fn windows(&self) -> Windows {
        self.windows
    }

    #[must_use]
    pub fn valid_device(device: &str) -> bool {
        !device.is_empty() && device.len() <= MAX_DEVICE && !device.chars().any(char::is_control)
    }

    #[must_use]
    pub fn knows(&self, device: &str) -> bool {
        self.threads.contains_key(device)
    }

    fn thread(&mut self, device: &str) -> Option<&mut VecDeque<Turn>> {
        if !Self::valid_device(device) {
            return None;
        }
        if !self.threads.contains_key(device) && self.threads.len() >= MAX_DEVICES {
            let oldest = self
                .threads
                .iter()
                .min_by(|a, b| {
                    let at = |t: &VecDeque<Turn>| t.back().map_or(f64::MIN, |x| x.at);
                    at(a.1).total_cmp(&at(b.1))
                })
                .map(|(k, _)| k.clone());
            if let Some(key) = oldest {
                self.threads.remove(&key);
            }
        }
        Some(self.threads.entry(device.to_owned()).or_default())
    }

    pub fn load(&mut self, device: &str, stored: Vec<Turn>) -> bool {
        let Some(thread) = self.thread(device) else {
            return false;
        };
        let mut merged: Vec<Turn> = stored
            .into_iter()
            .filter(|t| {
                !thread
                    .iter()
                    .any(|k| k.text == t.text && k.at.to_bits() == t.at.to_bits())
            })
            .collect();
        merged.extend(thread.drain(..));
        merged.sort_by(|a, b| a.at.total_cmp(&b.at));
        let skip = merged.len().saturating_sub(KEEP);
        thread.extend(merged.into_iter().skip(skip));
        true
    }

    pub fn remember(&mut self, device: &str, turn: Turn) -> bool {
        let Some(thread) = self.thread(device) else {
            return false;
        };
        thread.push_back(turn);
        while thread.len() > KEEP {
            thread.pop_front();
        }
        true
    }

    pub fn forget(&mut self, device: Option<&str>) -> usize {
        if let Some(d) = device {
            return self.threads.remove(d).map_or(0, |t| t.len());
        }
        let count = self.threads.values().map(VecDeque::len).sum();
        self.threads.clear();
        count
    }

    fn within(&self, device: &str, now: f64, window: f64) -> Vec<&Turn> {
        self.threads
            .get(device)
            .map(|t| t.iter().filter(|x| now - x.at < window).collect())
            .unwrap_or_default()
    }

    #[must_use]
    pub fn recent(&self, device: &str, now: f64) -> Vec<&Turn> {
        self.within(device, now, self.windows.stale)
    }

    #[must_use]
    pub fn last(&self, device: &str, now: f64) -> Option<&Turn> {
        self.recent(device, now).pop()
    }

    #[must_use]
    pub fn asked_question(&self, device: &str, now: f64) -> bool {
        self.last(device, now)
            .is_some_and(|t| t.reply.trim_end().ends_with('?') && now - t.at < QUESTION_S)
    }

    #[must_use]
    pub fn since_reply(&self, device: &str, now: f64) -> f64 {
        self.last(device, now).map_or(NO_REPLY, |t| now - t.at)
    }

    #[must_use]
    pub fn wants_resume(&self, text: &str) -> bool {
        self.patterns.resume.is_match(text)
    }

    fn lines(turns: &[&Turn]) -> String {
        let mut out: Vec<String> = Vec::with_capacity(turns.len().saturating_mul(2));
        for t in turns {
            let who = if t.who.is_empty() {
                "Utente"
            } else {
                t.who.as_str()
            };
            out.push(format!("{who}: {}", t.text));
            out.push(format!("Nuxiva: {}", clip(&t.reply, CONTEXT_REPLY)));
        }
        out.join("\n")
    }

    #[must_use]
    pub fn context(&self, device: &str, now: f64, text: &str) -> String {
        let recent = self.recent(device, now);
        if !recent.is_empty() {
            let skip = recent.len().saturating_sub(CONTEXT_TURNS);
            return Self::lines(recent.get(skip..).unwrap_or_default());
        }
        let window = if self.wants_resume(text) {
            self.windows.recall
        } else {
            self.windows.resume
        };
        let older = self.within(device, now, window);
        let Some(last) = older.last() else {
            return String::new();
        };
        #[allow(clippy::cast_possible_truncation)]
        let minutes = ((now - last.at) / 60.0).round().max(1.0) as i64;
        let skip = older.len().saturating_sub(RESUME_TURNS);
        format!(
            "Conversazione ripresa dopo {minutes} minuti. Ultimi scambi:\n{}",
            Self::lines(older.get(skip..).unwrap_or_default())
        )
    }

    #[must_use]
    pub fn resolve(&self, device: &str, text: &str, now: f64) -> String {
        let p = &self.patterns;
        let (Some(last), Some(caps)) = (self.last(device, now), p.ellipsis.captures(text)) else {
            return text.to_owned();
        };
        if !SKILL_INTENTS.contains(&last.intent.as_str()) {
            return text.to_owned();
        }
        let rest = caps
            .name("rest")
            .map_or("", |m| m.as_str())
            .trim_matches(PUNCT);
        let new_time = p.time.find(rest).map(|m| m.as_str().to_owned());
        let new_place = p.place.find(rest).map(|m| m.as_str().to_owned());
        if new_time.is_none() && new_place.is_none() {
            return text.to_owned();
        }
        let mut base = last.text.trim_end_matches(PUNCT).to_owned();
        if let Some(t) = &new_time {
            base = if p.time.is_match(&base) {
                p.time.replacen(&base, 1, NoExpand(t)).into_owned()
            } else {
                format!("{base} {t}")
            };
        }
        if let Some(place) = &new_place {
            base = if p.place.is_match(&base) {
                p.place.replacen(&base, 1, NoExpand(place)).into_owned()
            } else {
                format!("{base} {place}")
            };
        }
        base.push('?');
        base
    }
}
