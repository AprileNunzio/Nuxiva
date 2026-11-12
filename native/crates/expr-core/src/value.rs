use std::fmt::Write as _;

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i128),
    Float(f64),
    Str(String),
    List(Vec<Value>),
    Map(Vec<(Value, Value)>),
    Func(String),
    Opaque(String),
}

impl Value {
    #[must_use]
    pub fn truthy(&self) -> bool {
        match self {
            Self::Null => false,
            Self::Bool(b) => *b,
            Self::Int(i) => *i != 0,
            Self::Float(f) => *f != 0.0,
            Self::Str(s) => !s.is_empty(),
            Self::List(l) => !l.is_empty(),
            Self::Map(m) => !m.is_empty(),
            Self::Func(_) | Self::Opaque(_) => true,
        }
    }

    #[must_use]
    pub fn as_int(&self) -> Option<i128> {
        match self {
            Self::Bool(b) => Some(i128::from(*b)),
            Self::Int(i) => Some(*i),
            _ => None,
        }
    }

    #[must_use]
    pub fn is_numeric(&self) -> bool {
        matches!(self, Self::Bool(_) | Self::Int(_) | Self::Float(_))
    }

    #[must_use]
    #[allow(clippy::cast_precision_loss)]
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Self::Bool(b) => Some(f64::from(u8::from(*b))),
            Self::Int(i) => Some(*i as f64),
            Self::Float(f) => Some(*f),
            _ => None,
        }
    }

    #[must_use]
    pub fn hashable(&self) -> bool {
        match self {
            Self::List(_) | Self::Map(_) => false,
            Self::Null
            | Self::Bool(_)
            | Self::Int(_)
            | Self::Float(_)
            | Self::Str(_)
            | Self::Func(_)
            | Self::Opaque(_) => true,
        }
    }

    #[must_use]
    pub fn py_eq(&self, other: &Self) -> bool {
        match (self, other) {
            (a, b) if a.is_numeric() && b.is_numeric() => match (a.as_int(), b.as_int()) {
                (Some(x), Some(y)) => x == y,
                _ => a.as_f64() == b.as_f64(),
            },
            (Self::Null, Self::Null) => true,
            (Self::Str(a), Self::Str(b)) | (Self::Func(a), Self::Func(b)) => a == b,
            (Self::List(a), Self::List(b)) => {
                a.len() == b.len() && a.iter().zip(b).all(|(x, y)| x.py_eq(y))
            }
            (Self::Map(a), Self::Map(b)) => {
                a.len() == b.len()
                    && a.iter()
                        .all(|(k, v)| lookup(b, k).is_some_and(|w| w.py_eq(v)))
            }
            _ => false,
        }
    }

    #[must_use]
    pub fn py_str(&self) -> String {
        match self {
            Self::Str(s) | Self::Opaque(s) => s.clone(),
            other => other.py_repr(),
        }
    }

    #[must_use]
    pub fn py_repr(&self) -> String {
        match self {
            Self::Null => "None".to_owned(),
            Self::Bool(true) => "True".to_owned(),
            Self::Bool(false) => "False".to_owned(),
            Self::Int(i) => i.to_string(),
            Self::Float(f) => float_repr(*f),
            Self::Str(s) => str_repr(s),
            Self::List(items) => format!(
                "[{}]",
                items
                    .iter()
                    .map(Self::py_repr)
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            Self::Map(pairs) => format!(
                "{{{}}}",
                pairs
                    .iter()
                    .map(|(k, v)| format!("{}: {}", k.py_repr(), v.py_repr()))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            Self::Func(name) => format!("<function {name}>"),
            Self::Opaque(s) => s.clone(),
        }
    }
}

#[must_use]
pub fn lookup<'a>(pairs: &'a [(Value, Value)], key: &Value) -> Option<&'a Value> {
    pairs
        .iter()
        .rev()
        .find(|(k, _)| k.py_eq(key))
        .map(|(_, v)| v)
}

pub fn insert(pairs: &mut Vec<(Value, Value)>, key: Value, value: Value) {
    if let Some(slot) = pairs.iter_mut().find(|(k, _)| k.py_eq(&key)) {
        slot.1 = value;
    } else {
        pairs.push((key, value));
    }
}

#[must_use]
pub fn float_repr(f: f64) -> String {
    if f.is_nan() {
        return "nan".to_owned();
    }
    if f.is_infinite() {
        return if f > 0.0 {
            "inf".to_owned()
        } else {
            "-inf".to_owned()
        };
    }
    if f == 0.0 {
        return if f.is_sign_negative() {
            "-0.0".to_owned()
        } else {
            "0.0".to_owned()
        };
    }
    let sci = format!("{f:e}");
    let (mantissa, exp) = sci.split_once('e').unwrap_or((sci.as_str(), "0"));
    let exp: i32 = exp.parse().unwrap_or(0);
    let negative = mantissa.starts_with('-');
    let digits: String = mantissa.chars().filter(char::is_ascii_digit).collect();
    let sign = if negative { "-" } else { "" };
    if (-4..16).contains(&exp) {
        let len = i32::try_from(digits.len()).unwrap_or(i32::MAX);
        let body = if exp >= 0 {
            let int_len = exp.saturating_add(1);
            if len <= int_len {
                let zeros = usize::try_from(int_len.saturating_sub(len)).unwrap_or(0);
                format!("{digits}{}.0", "0".repeat(zeros))
            } else {
                let cut = usize::try_from(int_len).unwrap_or(0);
                format!(
                    "{}.{}",
                    digits.get(..cut).unwrap_or(""),
                    digits.get(cut..).unwrap_or("")
                )
            }
        } else {
            let zeros = usize::try_from(exp.saturating_neg().saturating_sub(1)).unwrap_or(0);
            format!("0.{}{digits}", "0".repeat(zeros))
        };
        return format!("{sign}{body}");
    }
    let first = digits.get(..1).unwrap_or("0");
    let rest = digits.get(1..).unwrap_or("");
    let mant = if rest.is_empty() {
        first.to_owned()
    } else {
        format!("{first}.{rest}")
    };
    let esign = if exp < 0 { "-" } else { "+" };
    format!("{sign}{mant}e{esign}{:02}", exp.unsigned_abs())
}

#[must_use]
pub fn str_repr(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::with_capacity(s.len().saturating_add(2));
    out.push(quote);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if (c as u32) < 0x20 || c as u32 == 0x7f => {
                let _ = write!(out, "\\x{:02x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push(quote);
    out
}

#[must_use]
pub fn number_text(text: &str) -> Option<f64> {
    let clean = text.replace(',', ".");
    let trimmed = clean.trim();
    let plain: String = if trimmed.contains('_') && valid_underscores(trimmed) {
        trimmed.replace('_', "")
    } else {
        trimmed.to_owned()
    };
    let lower = plain.to_lowercase();
    let body = lower.trim_start_matches(['+', '-']);
    let special = matches!(body, "inf" | "infinity" | "nan");
    if !special
        && !body
            .chars()
            .all(|c| c.is_ascii_digit() || matches!(c, '.' | 'e' | '+' | '-'))
    {
        return None;
    }
    plain.parse::<f64>().ok()
}

fn valid_underscores(text: &str) -> bool {
    let chars: Vec<char> = text.chars().collect();
    chars.iter().enumerate().all(|(i, c)| {
        *c != '_'
            || (i > 0
                && chars
                    .get(i.saturating_sub(1))
                    .is_some_and(char::is_ascii_digit)
                && chars
                    .get(i.saturating_add(1))
                    .is_some_and(char::is_ascii_digit))
    })
}

#[must_use]
pub fn parse_number(value: &Value) -> Option<f64> {
    match value {
        Value::Bool(_) | Value::Null | Value::List(_) | Value::Map(_) | Value::Func(_) => {
            number_text(&value.py_str())
        }
        Value::Int(_) | Value::Float(_) => value.as_f64(),
        Value::Str(s) | Value::Opaque(s) => number_text(s),
    }
}

#[must_use]
pub fn number(value: &Value, default: f64) -> f64 {
    parse_number(value).unwrap_or(default)
}
