use std::net::{IpAddr, Ipv6Addr};

use crate::percent::{latin1, quote};
use crate::text::py_strip;

const LOOPBACK: [&str; 3] = ["127.0.0.1", "::1", "localhost"];
const EXEMPT: [&str; 4] = [
    "/nuxiva-ca.crt",
    "/api/secure/status",
    "/healthz",
    "/api/health",
];
const PATH_SAFE: &str = "/-._~";
const QUERY_SAFE: &str = "=&-._~%+";

#[derive(Debug, Clone, Copy)]
pub struct RedirectRequest<'a> {
    pub scheme: &'a str,
    pub client: &'a str,
    pub path: &'a str,
    pub method: &'a str,
    pub fetch_mode: &'a str,
    pub accept: &'a str,
    pub host: &'a str,
    pub query: &'a [u8],
}

fn compressed_v6(address: Ipv6Addr) -> String {
    let segments = address.segments();
    let mut best: Option<(usize, usize)> = None;
    let mut run: Option<(usize, usize)> = None;
    for (index, segment) in segments.iter().enumerate() {
        if *segment == 0 {
            let (start, len) =
                run.map_or((index, 1), |(start, len)| (start, len.saturating_add(1)));
            run = Some((start, len));
            if len > 1 && best.is_none_or(|(_, top)| len > top) {
                best = Some((start, len));
            }
        } else {
            run = None;
        }
    }
    let hex = |items: &[u16]| {
        items
            .iter()
            .map(|s| format!("{s:x}"))
            .collect::<Vec<_>>()
            .join(":")
    };
    match best {
        None => hex(&segments),
        Some((start, len)) => {
            let head = segments.get(..start).unwrap_or_default();
            let tail = segments
                .get(start.saturating_add(len)..)
                .unwrap_or_default();
            format!("{}::{}", hex(head), hex(tail))
        }
    }
}

fn split_port(text: &str) -> Option<&str> {
    match text.rsplit_once(':') {
        None => Some(text),
        Some((head, port)) => {
            let ok = (1..=5).contains(&port.len()) && port.bytes().all(|b| b.is_ascii_digit());
            ok.then_some(head)
        }
    }
}

fn valid_name(name: &str) -> bool {
    (1..=253).contains(&name.len())
        && name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'.' || b == b'-')
}

fn valid_v6(inner: &str) -> bool {
    (2..=45).contains(&inner.len())
        && inner
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b) || b == b':' || b == b'.')
}

#[must_use]
pub fn safe_host(authority: &str) -> String {
    let lowered = py_strip(authority).to_lowercase();
    if let Some(rest) = lowered.strip_prefix('[') {
        let Some((inner, tail)) = rest.split_once(']') else {
            return String::new();
        };
        let port_ok = tail.is_empty() || split_port(&format!("x{tail}")).is_some_and(|h| h == "x");
        if !valid_v6(inner) || !port_ok {
            return String::new();
        }
        return match inner.parse::<IpAddr>() {
            Ok(IpAddr::V6(v6)) => format!("[{}]", compressed_v6(v6)),
            Ok(IpAddr::V4(v4)) => v4.to_string(),
            Err(_) => String::new(),
        };
    }
    let Some(name) = split_port(&lowered) else {
        return String::new();
    };
    if !valid_name(name) {
        return String::new();
    }
    match name.parse::<IpAddr>() {
        Ok(IpAddr::V4(v4)) => v4.to_string(),
        Ok(IpAddr::V6(v6)) => format!("[{}]", compressed_v6(v6)),
        Err(_) if name.contains("..") || name.starts_with(['.', '-']) => String::new(),
        Err(_) => name.to_owned(),
    }
}

fn navigation(request: &RedirectRequest<'_>) -> bool {
    let method = if request.method.is_empty() {
        "GET".to_owned()
    } else {
        request.method.to_ascii_uppercase()
    };
    if method != "GET" && method != "HEAD" {
        return false;
    }
    if !request.fetch_mode.is_empty() {
        return request.fetch_mode.eq_ignore_ascii_case("navigate");
    }
    request.accept.to_lowercase().contains("text/html")
}

#[must_use]
pub fn redirect_target(request: &RedirectRequest<'_>, admin: bool, port: i64) -> String {
    if request.scheme != "http" || port <= 0 || port > 65535 {
        return String::new();
    }
    if LOOPBACK.contains(&request.client) {
        return String::new();
    }
    let path = if request.path.is_empty() {
        "/"
    } else {
        request.path
    };
    if EXEMPT.iter().any(|p| path.starts_with(p)) || !navigation(request) {
        return String::new();
    }
    let host = safe_host(request.host);
    if host.is_empty() {
        return String::new();
    }
    let authority = if port == 443 {
        host
    } else {
        format!("{host}:{port}")
    };
    let prefix = if admin { "/admin" } else { "" };
    let target = format!("https://{authority}{prefix}{}", quote(path, PATH_SAFE));
    if request.query.is_empty() {
        target
    } else {
        format!("{target}?{}", quote(&latin1(request.query), QUERY_SAFE))
    }
}
