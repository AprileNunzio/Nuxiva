use regex::{Captures, Regex};
use serde::{Deserialize, Serialize};

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{Kind, Level, NodeRef, SELF_KEY};

pub const MAX_TEXT: usize = 4_000;
pub const MAX_FACTS: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Fact {
    pub from: NodeRef,
    pub relation: String,
    pub to: NodeRef,
    #[serde(default)]
    pub detail: Option<String>,
    pub confidence: u32,
    #[serde(default = "private")]
    pub level: Level,
}

const fn private() -> Level {
    Level::Private
}

const OBJ: &str = r"[\p{L}0-9][\p{L}0-9'’ \-]{0,60}";

struct Rule {
    pattern: Regex,
    relation: &'static str,
    negated: Option<&'static str>,
    kind: Kind,
    base: u32,
    mapped: bool,
    detail: bool,
}

#[derive(Debug)]
pub struct Extractor {
    rules: Vec<Rule>,
    cut: Regex,
    article: Regex,
}

impl std::fmt::Debug for Rule {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Rule(..)")
    }
}

fn kin(word: &str) -> Option<&'static str> {
    let w = word.to_lowercase();
    let relation = match w.as_str() {
        "moglie" | "marito" | "compagna" | "compagno" | "wife" | "husband" | "partner" => "spouse",
        "figlio" | "figlia" | "son" | "daughter" => "child",
        "fratello" | "sorella" | "brother" | "sister" => "sibling",
        "padre" | "madre" | "papà" | "papa" | "mamma" | "father" | "mother" => "parent",
        "nonno" | "nonna" | "grandfather" | "grandmother" => "grandparent",
        "amico" | "amica" | "friend" => "friend",
        "collega" | "colleague" => "colleague",
        _ => return None,
    };
    Some(relation)
}

fn rule(pattern: &str, relation: &'static str, kind: Kind, base: u32) -> KnowledgeResult<Rule> {
    Ok(Rule {
        pattern: Regex::new(pattern).map_err(|_| KnowledgeError::Settings)?,
        relation,
        negated: None,
        kind,
        base,
        mapped: false,
        detail: false,
    })
}

impl Extractor {
    #[allow(clippy::too_many_lines)]
    pub fn new() -> KnowledgeResult<Self> {
        let like_it = format!(
            r"(?i)\b(?P<neg>non\s+)?(?:mi\s+piace(?:no)?|adoro|amo)\s+(?:molto\s+|tanto\s+|tantissimo\s+)?(?P<o>{OBJ})"
        );
        let like_en = format!(
            r"(?i)\bi\s+(?P<neg>(?:do\s*n['’]?t|do\s+not)\s+)?(?:really\s+)?(?:like|love|enjoy)\s+(?P<o>{OBJ})"
        );
        let kin_words = "moglie|marito|compagna|compagno|figlio|figlia|fratello|sorella|padre|madre|pap[àa]|mamma|nonno|nonna|amico|amica|collega";
        let kin_en = "wife|husband|partner|son|daughter|brother|sister|father|mother|grandfather|grandmother|friend|colleague";
        let pets = "cane|gatto|cavallo|pesce|coniglio|criceto|dog|cat|horse|fish|rabbit|hamster";
        let mut like = rule(&like_it, "likes", Kind::Preference, 750)?;
        like.negated = Some("dislikes");
        let mut like_en_rule = rule(&like_en, "likes", Kind::Preference, 750)?;
        like_en_rule.negated = Some("dislikes");
        let mut relative = rule(
            &format!(
                r"(?i)\bmi[oa]\s+(?P<rel>{kin_words})\s+(?:si\s+chiama|di\s+nome)\s+(?P<o>{OBJ})"
            ),
            "",
            Kind::Person,
            800,
        )?;
        relative.mapped = true;
        let mut relative_en = rule(
            &format!(
                r"(?i)\bmy\s+(?P<rel>{kin_en})\s+(?:is\s+called|is\s+named|named)\s+(?P<o>{OBJ})"
            ),
            "",
            Kind::Person,
            800,
        )?;
        relative_en.mapped = true;
        let mut pet = rule(
            &format!(
                r"(?i)\b(?:il\s+mio|la\s+mia|ho\s+un|ho\s+una)\s+(?P<pet>{pets})\s+(?:che\s+)?(?:si\s+chiama|di\s+nome)\s+(?P<o>{OBJ})"
            ),
            "owns_pet",
            Kind::Object,
            800,
        )?;
        pet.detail = true;
        let mut pet_en = rule(
            &format!(
                r"(?i)\bmy\s+(?P<pet>{pets})\s+(?:is\s+called|is\s+named|named)\s+(?P<o>{OBJ})"
            ),
            "owns_pet",
            Kind::Object,
            800,
        )?;
        pet_en.detail = true;
        let rules = vec![
            like,
            like_en_rule,
            rule(
                &format!(r"(?i)\b(?:odio|detesto)\s+(?P<o>{OBJ})"),
                "dislikes",
                Kind::Preference,
                750,
            )?,
            rule(
                &format!(r"(?i)\bi\s+(?:really\s+)?(?:hate|dislike)\s+(?P<o>{OBJ})"),
                "dislikes",
                Kind::Preference,
                750,
            )?,
            rule(
                &format!(r"(?i)\b(?:abito|vivo|risiedo)\s+(?:a|ad|in|nel|nella)\s+(?P<o>{OBJ})"),
                "lives_in",
                Kind::Place,
                800,
            )?,
            rule(
                &format!(r"(?i)\bi\s+live\s+in\s+(?P<o>{OBJ})"),
                "lives_in",
                Kind::Place,
                800,
            )?,
            rule(
                &format!(r"(?i)\blavoro\s+come\s+(?P<o>{OBJ})"),
                "works_as",
                Kind::Concept,
                800,
            )?,
            rule(
                &format!(r"(?i)\bi\s+work\s+as\s+(?:an?\s+)?(?P<o>{OBJ})"),
                "works_as",
                Kind::Concept,
                800,
            )?,
            rule(
                &format!(r"(?i)\blavoro\s+(?:a|presso|per)\s+(?P<o>{OBJ})"),
                "works_at",
                Kind::Place,
                800,
            )?,
            rule(
                &format!(r"(?i)\bi\s+work\s+(?:at|for)\s+(?P<o>{OBJ})"),
                "works_at",
                Kind::Place,
                800,
            )?,
            rule(
                &format!(r"(?i)\bsono\s+nat[oa]\s+(?:a|ad|in)\s+(?P<o>{OBJ})"),
                "born_in",
                Kind::Place,
                800,
            )?,
            rule(
                &format!(r"(?i)\bi\s+was\s+born\s+in\s+(?P<o>{OBJ})"),
                "born_in",
                Kind::Place,
                800,
            )?,
            relative,
            relative_en,
            pet,
            pet_en,
            rule(
                &format!(
                    r"(?i)\b(?P<o>(?:ogni|tutte\s+le|tutti\s+i)\s+(?:mattina|sera|notte|giorno|giorni|domenica|sabato|lunedì|martedì|mercoledì|giovedì|venerdì)\s+{OBJ})"
                ),
                "has_habit",
                Kind::Habit,
                600,
            )?,
            rule(
                &format!(
                    r"(?i)\b(?P<o>every\s+(?:morning|evening|night|day|sunday|saturday|monday|tuesday|wednesday|thursday|friday)\s+{OBJ})"
                ),
                "has_habit",
                Kind::Habit,
                600,
            )?,
        ];
        Ok(Self {
            rules,
            cut: Regex::new(
                r"(?i)[,.;:!?()]|\s(?:e|ma|and|but|perché|perche|because|però|quando|when|che)\s",
            )
            .map_err(|_| KnowledgeError::Settings)?,
            article: Regex::new(r"(?i)^(?:(?:il|lo|la|i|gli|le|un|uno|una|the|a|an|my)\s+|l['’])")
                .map_err(|_| KnowledgeError::Settings)?,
        })
    }

    fn object(&self, raw: &str, kind: Kind) -> Option<String> {
        let head = self.cut.split(raw).next().unwrap_or("").trim();
        let stripped = if matches!(kind, Kind::Preference | Kind::Concept | Kind::Object) {
            self.article.replace(head, "").trim().to_owned()
        } else {
            head.to_owned()
        };
        let chars = stripped.chars().count();
        let stop = ["questo", "quello", "non", "this", "that", "it", "molto"];
        let blocked = stop.contains(&stripped.to_lowercase().as_str());
        ((2..=60).contains(&chars) && !blocked).then_some(stripped)
    }

    pub fn extract(&self, text: &str) -> KnowledgeResult<Vec<Fact>> {
        if text.chars().count() > MAX_TEXT {
            return Err(KnowledgeError::TooLarge);
        }
        if text
            .chars()
            .any(|c| c.is_control() && c != '\n' && c != '\t')
        {
            return Err(KnowledgeError::Invalid);
        }
        let mut facts: Vec<Fact> = Vec::new();
        for rule in &self.rules {
            for caps in rule.pattern.captures_iter(text) {
                if let Some(fact) = self.build(rule, &caps) {
                    let dup = facts.iter().any(|f| {
                        f.relation == fact.relation
                            && crate::text::normalize(&f.to.label)
                                == crate::text::normalize(&fact.to.label)
                    });
                    if !dup {
                        facts.push(fact);
                    }
                }
            }
        }
        facts.truncate(MAX_FACTS);
        Ok(facts)
    }

    fn build(&self, rule: &Rule, caps: &Captures<'_>) -> Option<Fact> {
        let label = self.object(caps.name("o")?.as_str(), rule.kind)?;
        let relation = if rule.mapped {
            kin(caps.name("rel")?.as_str())?
        } else if caps.name("neg").is_some() {
            rule.negated?
        } else {
            rule.relation
        };
        let detail = if rule.detail {
            caps.name("pet").map(|m| m.as_str().to_lowercase())
        } else {
            None
        };
        Some(Fact {
            from: NodeRef {
                kind: Kind::Person,
                label: SELF_KEY.to_owned(),
            },
            relation: relation.to_owned(),
            to: NodeRef {
                kind: rule.kind,
                label,
            },
            detail,
            confidence: rule.base,
            level: Level::Private,
        })
    }
}
