use base64::Engine;
use base64::alphabet::URL_SAFE;
use base64::engine::{DecodePaddingMode, GeneralPurpose, GeneralPurposeConfig};
use serde_json::Value;

use crate::error::{MobileError, MobileResult};

const SCHEME: &str = "nuxiva://";
const HOST: &str = "enroll";
const PARAMETER: &str = "d";
const BODY_LIMIT: usize = 4096;
const LINK_LIMIT: usize = 8192;
const CODE_LENGTH: usize = 6;
const INVALID: &str = "enroll_file_invalid";
const EXPIRED: &str = "enroll_file_expired";
const CODE_INVALID: &str = "enroll_code_invalid";

const DECODER: GeneralPurpose = GeneralPurpose::new(
    &URL_SAFE,
    GeneralPurposeConfig::new()
        .with_encode_padding(false)
        .with_decode_padding_mode(DecodePaddingMode::RequireNone)
        .with_decode_allow_trailing_bits(true),
);

#[derive(Debug, Clone, PartialEq, Eq, uniffi::Record)]
pub struct EnrollmentPayload {
    pub server: String,
    pub token: String,
    pub pin: String,
    pub expires: i64,
    pub peer: String,
}

fn invalid() -> MobileError {
    MobileError::code(INVALID)
}

fn starts_with_ignore_case(text: &str, prefix: &str) -> bool {
    text.get(..prefix.len())
        .is_some_and(|head| head.eq_ignore_ascii_case(prefix))
}

fn is_token(value: &str) -> bool {
    (20..=128).contains(&value.len())
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

fn is_pin(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

fn is_label(label: &str) -> bool {
    let bytes = label.as_bytes();
    let edge = |b: &u8| b.is_ascii_alphanumeric() || *b == b'_';
    match (bytes.first(), bytes.last()) {
        (Some(first), Some(last)) => {
            edge(first) && edge(last) && bytes.iter().all(|b| edge(b) || *b == b'-')
        }
        _ => false,
    }
}

fn valid_host(host: &str) -> bool {
    if let Some(inner) = host.strip_prefix('[').and_then(|h| h.strip_suffix(']')) {
        return !inner.is_empty()
            && inner
                .bytes()
                .all(|b| b.is_ascii_hexdigit() || b == b':' || b == b'.');
    }
    let trimmed = host.strip_suffix('.').unwrap_or(host);
    !trimmed.is_empty() && trimmed.split('.').all(is_label)
}

fn split_port(rest: &str) -> MobileResult<(&str, Option<u32>)> {
    let (host, port) = if rest.starts_with('[') {
        let close = rest.find(']').ok_or_else(invalid)?;
        let (host, tail) = rest.split_at(close.checked_add(1).ok_or_else(invalid)?);
        (host, tail)
    } else {
        match rest.find(':') {
            Some(index) => rest.split_at(index),
            None => (rest, ""),
        }
    };
    if port.is_empty() {
        return Ok((host, None));
    }
    let digits = port.strip_prefix(':').ok_or_else(invalid)?;
    if digits.is_empty() || digits.len() > 5 || !digits.bytes().all(|b| b.is_ascii_digit()) {
        return Err(invalid());
    }
    let number: u32 = digits.parse().map_err(|_| invalid())?;
    Ok((host, Some(number)))
}

pub fn normalize_server(value: &str) -> MobileResult<String> {
    let text = value.trim();
    if !starts_with_ignore_case(text, "https://") {
        return Err(invalid());
    }
    let rest = text.get("https://".len()..).ok_or_else(invalid)?;
    let rest = rest.strip_suffix('/').unwrap_or(rest);
    let (host, port) = split_port(rest)?;
    if !valid_host(host) {
        return Err(invalid());
    }
    match port {
        None | Some(443) => Ok(format!("https://{host}")),
        Some(p) if (1..=65_535).contains(&p) => Ok(format!("https://{host}:{p}")),
        Some(_) => Err(invalid()),
    }
}

fn percent_decode(raw: &str) -> MobileResult<String> {
    let bytes = raw.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0usize;
    while let Some(&byte) = bytes.get(index) {
        if byte == b'%' {
            let pair = bytes
                .get(index.saturating_add(1)..index.saturating_add(3))
                .ok_or_else(invalid)?;
            let text = std::str::from_utf8(pair).map_err(|_| invalid())?;
            out.push(u8::from_str_radix(text, 16).map_err(|_| invalid())?);
            index = index.saturating_add(3);
        } else {
            out.push(byte);
            index = index.saturating_add(1);
        }
    }
    String::from_utf8(out).map_err(|_| invalid())
}

fn decode(encoded: &str) -> MobileResult<String> {
    let clean = encoded.trim_end_matches('=');
    if clean.is_empty()
        || !clean
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
    {
        return Err(invalid());
    }
    let bytes = DECODER.decode(clean).map_err(|_| invalid())?;
    String::from_utf8(bytes).map_err(|_| invalid())
}

fn from_link(link: &str) -> MobileResult<String> {
    let rest = link.get(SCHEME.len()..).ok_or_else(invalid)?;
    let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    let (authority, tail) = rest.split_at(end);
    if !authority.eq_ignore_ascii_case(HOST) {
        return Err(invalid());
    }
    let query = tail.split_once('?').map_or("", |(_, q)| q);
    let query = query.split_once('#').map_or(query, |(q, _)| q);
    let encoded = query
        .split('&')
        .filter_map(|pair| pair.split_once('=').or(Some((pair, ""))))
        .find(|(name, _)| *name == PARAMETER)
        .map(|(_, value)| value)
        .ok_or_else(invalid)?;
    decode(&percent_decode(encoded)?)
}

fn field(value: Option<&Value>) -> Option<&str> {
    value.and_then(Value::as_str)
}

fn expiry(value: Option<&Value>) -> Option<i64> {
    let number = value?.as_number()?;
    number.as_i64().or_else(|| {
        number
            .as_f64()
            .filter(|f| f.is_finite() && f.abs() < 9.0e15)
            .map(|f| {
                #[allow(clippy::cast_possible_truncation)]
                let whole = f.trunc() as i64;
                whole
            })
    })
}

#[uniffi::export]
pub fn parse_enrollment(raw: &str, now: i64) -> Result<EnrollmentPayload, MobileError> {
    let text: String = raw
        .chars()
        .filter(|c| !c.is_whitespace() && *c != '\u{200b}' && *c != '\u{feff}')
        .collect();
    let text = text
        .strip_prefix('"')
        .and_then(|t| t.strip_suffix('"'))
        .or_else(|| text.strip_prefix('\'').and_then(|t| t.strip_suffix('\'')))
        .unwrap_or(&text);
    if text.is_empty() || text.len() > LINK_LIMIT {
        return Err(invalid());
    }
    let body = if starts_with_ignore_case(text, SCHEME) {
        from_link(text)?
    } else if text.starts_with('{') {
        raw.trim().to_owned()
    } else {
        decode(text)?
    };
    if body.len() > BODY_LIMIT {
        return Err(invalid());
    }
    let wire: Value = serde_json::from_str(&body).map_err(|_| invalid())?;
    let object = wire.as_object().ok_or_else(invalid)?;
    let server = normalize_server(field(object.get("server")).ok_or_else(invalid)?)?;
    let token = field(object.get("token"))
        .filter(|t| is_token(t))
        .ok_or_else(invalid)?;
    let pin = field(object.get("pin"))
        .filter(|p| is_pin(p))
        .ok_or_else(invalid)?;
    let expires = expiry(object.get("expires")).ok_or_else(invalid)?;
    let peer = match object.get("peer") {
        None => "",
        Some(value) => value
            .as_str()
            .filter(|p| p.is_empty() || is_pin(p))
            .ok_or_else(invalid)?,
    };
    if expires < now {
        return Err(MobileError::code(EXPIRED));
    }
    Ok(EnrollmentPayload {
        server,
        token: token.to_owned(),
        pin: pin.to_owned(),
        expires,
        peer: peer.to_owned(),
    })
}

#[uniffi::export]
pub fn normalize_code(value: &str) -> Result<String, MobileError> {
    let digits: String = value.chars().filter(char::is_ascii_digit).collect();
    if digits.len() == CODE_LENGTH {
        Ok(digits)
    } else {
        Err(MobileError::code(CODE_INVALID))
    }
}

#[uniffi::export]
pub fn normalize_server_input(value: &str) -> Result<String, MobileError> {
    let text = value.trim().trim_end_matches('/');
    if text.is_empty() || text.len() > 255 || text.chars().any(char::is_whitespace) {
        return Err(invalid());
    }
    if text.contains("://") {
        normalize_server(text)
    } else {
        normalize_server(&format!("https://{text}"))
    }
}
