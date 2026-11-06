use crate::Fault;

#[derive(Debug, Clone, PartialEq)]
pub enum Tok {
    Int(i128),
    Float(f64),
    Str(String),
    Name(String),
    Op(&'static str),
    End,
}

const OPS: [&str; 33] = [
    "**=", "//=", ">>=", "<<=", "**", "//", "==", "!=", "<=", ">=", "<<", ">>", ":=", "->", "+",
    "-", "*", "/", "%", "<", ">", "(", ")", "[", "]", "{", "}", ",", ":", ".", "|", "&", "^",
];
const MORE_OPS: [&str; 4] = ["~", "@", "=", ";"];

fn syntax(msg: &str) -> Fault {
    Fault::Expr(format!("sintassi non valida: {msg}"))
}

fn digits(chars: &[char], mut i: usize, ok: impl Fn(char) -> bool) -> (String, usize) {
    let mut out = String::new();
    while let Some(&c) = chars.get(i) {
        if ok(c) {
            out.push(c);
        } else if c != '_'
            || !chars.get(i.saturating_add(1)).is_some_and(|n| ok(*n))
            || out.is_empty()
        {
            break;
        }
        i = i.saturating_add(1);
    }
    (out, i)
}

fn number(chars: &[char], start: usize) -> Result<(Tok, usize), Fault> {
    let at = |i: usize| chars.get(i).copied().unwrap_or('\0');
    if at(start) == '0'
        && matches!(
            at(start.saturating_add(1)),
            'x' | 'X' | 'o' | 'O' | 'b' | 'B'
        )
    {
        let radix = match at(start.saturating_add(1)) {
            'x' | 'X' => 16,
            'o' | 'O' => 8,
            _ => 2,
        };
        let (body, end) = digits(chars, start.saturating_add(2), |c| c.is_digit(radix));
        let value = i128::from_str_radix(&body, radix).map_err(|_| syntax("numero non valido"))?;
        return Ok((Tok::Int(value), end));
    }
    let (int_part, mut i) = digits(chars, start, |c| c.is_ascii_digit());
    let mut text = int_part.clone();
    let mut float = false;
    if at(i) == '.' {
        float = true;
        let (frac, end) = digits(chars, i.saturating_add(1), |c| c.is_ascii_digit());
        text.push('.');
        text.push_str(&frac);
        i = end;
    }
    if matches!(at(i), 'e' | 'E') {
        let mut j = i.saturating_add(1);
        let mut exp = String::from("e");
        if matches!(at(j), '+' | '-') {
            exp.push(at(j));
            j = j.saturating_add(1);
        }
        let (body, end) = digits(chars, j, |c| c.is_ascii_digit());
        if body.is_empty() {
            return Err(syntax("numero non valido"));
        }
        exp.push_str(&body);
        text.push_str(&exp);
        float = true;
        i = end;
    }
    if matches!(at(i), 'j' | 'J') || at(i).is_alphanumeric() || at(i) == '_' {
        return Err(syntax("numero non valido"));
    }
    if float {
        let value: f64 = text.parse().map_err(|_| syntax("numero non valido"))?;
        return Ok((Tok::Float(value), i));
    }
    if int_part.len() > 1 && int_part.starts_with('0') && int_part.chars().any(|c| c != '0') {
        return Err(syntax("zeri iniziali non permessi"));
    }
    match int_part.parse::<i128>() {
        Ok(v) => Ok((Tok::Int(v), i)),
        Err(_) => int_part
            .parse::<f64>()
            .map(|v| (Tok::Float(v), i))
            .map_err(|_| syntax("numero non valido")),
    }
}

fn escape(chars: &[char], i: usize, out: &mut String) -> Result<usize, Fault> {
    let at = |k: usize| chars.get(k).copied().unwrap_or('\0');
    let c = at(i);
    let simple = match c {
        '\n' => Some(None),
        '\\' => Some(Some('\\')),
        '\'' => Some(Some('\'')),
        '"' => Some(Some('"')),
        'n' => Some(Some('\n')),
        't' => Some(Some('\t')),
        'r' => Some(Some('\r')),
        'a' => Some(Some('\u{7}')),
        'b' => Some(Some('\u{8}')),
        'f' => Some(Some('\u{c}')),
        'v' => Some(Some('\u{b}')),
        '0'..='7' | 'x' | 'u' | 'U' => None,
        _ => {
            out.push('\\');
            out.push(c);
            return Ok(i.saturating_add(1));
        }
    };
    if let Some(ch) = simple {
        if let Some(ch) = ch {
            out.push(ch);
        }
        return Ok(i.saturating_add(1));
    }
    let (len, radix, from) = match c {
        'x' => (2, 16, i.saturating_add(1)),
        'u' => (4, 16, i.saturating_add(1)),
        'U' => (8, 16, i.saturating_add(1)),
        _ => (3, 8, i),
    };
    let mut code = String::new();
    let mut k = from;
    while code.len() < len && at(k).is_digit(radix) {
        code.push(at(k));
        k = k.saturating_add(1);
    }
    if radix == 16 && code.len() != len {
        return Err(syntax("sequenza di escape non valida"));
    }
    let value =
        u32::from_str_radix(&code, radix).map_err(|_| syntax("sequenza di escape non valida"))?;
    out.push(char::from_u32(value).ok_or_else(|| syntax("sequenza di escape non valida"))?);
    Ok(k)
}

fn string(chars: &[char], start: usize, raw: bool) -> Result<(String, usize), Fault> {
    let at = |k: usize| chars.get(k).copied().unwrap_or('\0');
    let quote = at(start);
    let triple = at(start.saturating_add(1)) == quote && at(start.saturating_add(2)) == quote;
    let mut i = start.saturating_add(if triple { 3 } else { 1 });
    let mut out = String::new();
    loop {
        let Some(&c) = chars.get(i) else {
            return Err(syntax("stringa non chiusa"));
        };
        if c == quote
            && (!triple || (at(i.saturating_add(1)) == quote && at(i.saturating_add(2)) == quote))
        {
            return Ok((out, i.saturating_add(if triple { 3 } else { 1 })));
        }
        if c == '\n' && !triple {
            return Err(syntax("stringa non chiusa"));
        }
        if c == '\\' {
            if raw {
                out.push('\\');
                if let Some(&n) = chars.get(i.saturating_add(1)) {
                    out.push(n);
                }
                i = i.saturating_add(2);
            } else {
                i = escape(chars, i.saturating_add(1), &mut out)?;
            }
            continue;
        }
        out.push(c);
        i = i.saturating_add(1);
    }
}

pub fn tokenize(source: &str) -> Result<Vec<Tok>, Fault> {
    let chars: Vec<char> = source.chars().collect();
    let mut toks = Vec::new();
    let mut i = 0_usize;
    while let Some(&c) = chars.get(i) {
        let next = chars.get(i.saturating_add(1)).copied().unwrap_or('\0');
        if c.is_whitespace() {
            i = i.saturating_add(1);
        } else if c == '#' {
            while chars.get(i).is_some_and(|c| *c != '\n') {
                i = i.saturating_add(1);
            }
        } else if c == '\\' && next == '\n' {
            i = i.saturating_add(2);
        } else if c.is_ascii_digit() || (c == '.' && next.is_ascii_digit()) {
            let (tok, end) = number(&chars, i)?;
            toks.push(tok);
            i = end;
        } else if c == '\'' || c == '"' {
            let (s, end) = string(&chars, i, false)?;
            toks.push(Tok::Str(s));
            i = end;
        } else if c.is_alphabetic() || c == '_' {
            let mut name = String::new();
            let mut j = i;
            while chars
                .get(j)
                .is_some_and(|c| c.is_alphanumeric() || *c == '_')
            {
                if let Some(&ch) = chars.get(j) {
                    name.push(ch);
                }
                j = j.saturating_add(1);
            }
            let quote = chars.get(j).copied().unwrap_or('\0');
            if (quote == '\'' || quote == '"') && name.len() <= 2 {
                let lower = name.to_lowercase();
                if lower == "r" {
                    let (s, end) = string(&chars, j, true)?;
                    toks.push(Tok::Str(s));
                    i = end;
                    continue;
                }
                if lower == "u" {
                    let (s, end) = string(&chars, j, false)?;
                    toks.push(Tok::Str(s));
                    i = end;
                    continue;
                }
                if lower.chars().all(|c| matches!(c, 'b' | 'f' | 'r')) {
                    return Err(Fault::Expr(format!(
                        "costrutto non permesso: {}",
                        if lower.contains('f') {
                            "JoinedStr"
                        } else {
                            "bytes"
                        }
                    )));
                }
            }
            toks.push(Tok::Name(name));
            i = j;
        } else {
            let rest: String = chars.iter().skip(i).take(3).collect();
            let op = OPS
                .iter()
                .chain(MORE_OPS.iter())
                .find(|op| rest.starts_with(**op))
                .ok_or_else(|| syntax(&format!("carattere non valido '{c}'")))?;
            toks.push(Tok::Op(op));
            i = i.saturating_add(op.chars().count());
        }
    }
    toks.push(Tok::End);
    Ok(toks)
}
