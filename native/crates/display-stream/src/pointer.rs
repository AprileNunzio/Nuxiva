use crate::error::StreamError;
use crate::op::MAX_DEPTH;

#[must_use]
pub fn escape(token: &str) -> String {
    token.replace('~', "~0").replace('/', "~1")
}

#[must_use]
pub fn join(base: &str, token: &str) -> String {
    let mut out = String::with_capacity(base.len().saturating_add(token.len()).saturating_add(1));
    out.push_str(base);
    out.push('/');
    out.push_str(&escape(token));
    out
}

pub fn split(path: &str) -> Result<Vec<String>, StreamError> {
    if path.is_empty() {
        return Ok(Vec::new());
    }
    let rest = path.strip_prefix('/').ok_or(StreamError::Pointer)?;
    let tokens: Vec<String> = rest.split('/').map(unescape).collect::<Result<_, _>>()?;
    if tokens.len() > MAX_DEPTH {
        return Err(StreamError::TooDeep);
    }
    Ok(tokens)
}

fn unescape(token: &str) -> Result<String, StreamError> {
    let mut out = String::with_capacity(token.len());
    let mut chars = token.chars();
    while let Some(c) = chars.next() {
        if c == '~' {
            match chars.next() {
                Some('0') => out.push('~'),
                Some('1') => out.push('/'),
                _ => return Err(StreamError::Pointer),
            }
        } else {
            out.push(c);
        }
    }
    Ok(out)
}
