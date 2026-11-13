pub const MAX_INPUT: usize = 256 * 1024;
pub const MAX_LINES: usize = 400;
pub const MAX_TEXT: usize = 200;
pub const MAX_WORDS: usize = 64;
const MAX_WORD: usize = 60;
const MAX_OFFSET_MS: i64 = 60_000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LyricWord {
    pub t_ms: u32,
    pub text: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LyricLine {
    pub t_ms: u32,
    pub text: String,
    pub words: Vec<LyricWord>,
}

fn digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit())
}

fn stamp(body: &str) -> Option<u32> {
    let (mm, rest) = body.split_once(':')?;
    if mm.len() > 3 || !digits(mm) {
        return None;
    }
    let (ss, frac) = match rest.find(['.', ':']) {
        Some(i) => (rest.get(..i)?, Some(rest.get(i.saturating_add(1)..)?)),
        None => (rest, None),
    };
    if ss.len() != 2 || !digits(ss) {
        return None;
    }
    let minutes: u32 = mm.parse().ok()?;
    let seconds: u32 = ss.parse().ok()?;
    if seconds >= 60 {
        return None;
    }
    let fraction = match frac {
        None => 0,
        Some(f) => {
            if f.len() > 3 || !digits(f) {
                return None;
            }
            let v: u32 = f.parse().ok()?;
            match f.len() {
                1 => v.checked_mul(100)?,
                2 => v.checked_mul(10)?,
                _ => v,
            }
        }
    };
    minutes
        .checked_mul(60_000)?
        .checked_add(seconds.checked_mul(1_000)?)?
        .checked_add(fraction)
}

fn offset_tag(line: &str) -> Option<i64> {
    let body = line.strip_prefix('[')?.strip_suffix(']')?;
    let (key, value) = body.split_once(':')?;
    if !key.trim().eq_ignore_ascii_case("offset") {
        return None;
    }
    let value = value.trim();
    let (negative, number) = match value.strip_prefix('-') {
        Some(n) => (true, n),
        None => (false, value.strip_prefix('+').unwrap_or(value)),
    };
    if number.len() > 6 || !digits(number) {
        return None;
    }
    let v: i64 = number.parse().ok()?;
    let v = v.min(MAX_OFFSET_MS);
    Some(if negative { v.saturating_neg() } else { v })
}

fn clean(raw: &str, limit: usize) -> String {
    let spaced: String = raw
        .chars()
        .map(|c| if c.is_control() { ' ' } else { c })
        .collect();
    let joined = spaced.split_whitespace().collect::<Vec<_>>().join(" ");
    joined.chars().take(limit).collect()
}

fn split_words(text: &str) -> (String, Vec<LyricWord>) {
    let mut plain = String::new();
    let mut words = Vec::new();
    let mut current: Option<u32> = None;
    let mut buf = String::new();
    let mut rest = text;
    let mut flush = |buf: &mut String, at: Option<u32>, plain: &mut String| {
        if let Some(t) = at {
            let word = clean(buf, MAX_WORD);
            if !word.is_empty() && words.len() < MAX_WORDS {
                words.push(LyricWord {
                    t_ms: t,
                    text: word,
                });
            }
        }
        plain.push_str(buf);
        buf.clear();
    };
    while let Some(open) = rest.find('<') {
        let (before, tail) = rest.split_at(open);
        buf.push_str(before);
        let parsed = tail
            .find('>')
            .and_then(|close| tail.get(1..close).and_then(stamp).map(|t| (t, close)));
        if let Some((t, close)) = parsed {
            flush(&mut buf, current, &mut plain);
            current = Some(t);
            rest = tail.get(close.saturating_add(1)..).unwrap_or("");
        } else {
            buf.push('<');
            rest = tail.get(1..).unwrap_or("");
        }
    }
    buf.push_str(rest);
    flush(&mut buf, current, &mut plain);
    (clean(&plain, MAX_TEXT), words)
}

fn shift(t: u32, offset: i64) -> u32 {
    let moved = i64::from(t).saturating_sub(offset).max(0);
    u32::try_from(moved).unwrap_or(u32::MAX)
}

fn head(input: &str) -> &str {
    if input.len() <= MAX_INPUT {
        return input;
    }
    let mut end = MAX_INPUT;
    while end > 0 && !input.is_char_boundary(end) {
        end = end.saturating_sub(1);
    }
    input.get(..end).unwrap_or("")
}

#[must_use]
pub fn parse(input: &str) -> Vec<LyricLine> {
    let mut lines = Vec::new();
    let mut offset = 0_i64;
    for raw in head(input).lines() {
        let mut rest = raw.trim();
        let mut stamps = Vec::new();
        while let Some(body) = rest.strip_prefix('[') {
            let Some(end) = body.find(']') else { break };
            let Some(t) = body.get(..end).and_then(stamp) else {
                break;
            };
            stamps.push(t);
            rest = body.get(end.saturating_add(1)..).unwrap_or("");
        }
        if stamps.is_empty() {
            if let Some(v) = offset_tag(rest) {
                offset = v;
            }
            continue;
        }
        let (text, words) = split_words(rest);
        let single = stamps.len() == 1;
        for t in stamps {
            lines.push(LyricLine {
                t_ms: t,
                text: text.clone(),
                words: if single { words.clone() } else { Vec::new() },
            });
        }
    }
    for line in &mut lines {
        line.t_ms = shift(line.t_ms, offset);
        for word in &mut line.words {
            word.t_ms = shift(word.t_ms, offset);
        }
    }
    lines.sort_by_key(|l| l.t_ms);
    lines.truncate(MAX_LINES);
    lines
}
