use std::net::IpAddr;

const UNSAFE: [&str; 4] = ["POST", "PUT", "PATCH", "DELETE"];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OriginVerdict {
    Allow,
    UntrustedHost,
    CrossSite,
    ForeignOrigin,
}

impl OriginVerdict {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Allow => "",
            Self::UntrustedHost => "untrusted_host",
            Self::CrossSite => "cross_site",
            Self::ForeignOrigin => "foreign_origin",
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct OriginRequest<'a> {
    pub host: &'a str,
    pub method: &'a str,
    pub fetch_site: &'a str,
    pub origin: &'a str,
}

fn netloc_hostname(netloc: &str) -> Option<String> {
    let host = netloc.rsplit_once('@').map_or(netloc, |(_, h)| h);
    let has_open = host.contains('[');
    let has_close = host.contains(']');
    if has_open != has_close {
        return None;
    }
    let name = if has_open {
        let (_, after) = host.split_once('[')?;
        let (inside, _) = after.split_once(']')?;
        inside
    } else {
        host.split_once(':').map_or(host, |(h, _)| h)
    };
    Some(name.to_lowercase())
}

#[must_use]
pub fn authority_hostname(authority: &str) -> Option<String> {
    if authority.is_empty() {
        return Some(String::new());
    }
    let netloc = authority.split(['/', '?', '#']).next().unwrap_or_default();
    netloc_hostname(netloc)
}

fn split_scheme(url: &str) -> &str {
    if let Some((scheme, rest)) = url.split_once(':') {
        let mut chars = scheme.chars();
        let valid = chars.next().is_some_and(|c| c.is_ascii_alphabetic())
            && chars.all(|c| c.is_ascii_alphanumeric() || matches!(c, '+' | '-' | '.'));
        if valid {
            return rest;
        }
    }
    url
}

#[must_use]
pub fn origin_hostname(origin: &str) -> Option<String> {
    if origin.is_empty() || origin == "null" {
        return Some(String::new());
    }
    let rest = split_scheme(origin);
    let Some(after) = rest.strip_prefix("//") else {
        return Some(String::new());
    };
    let netloc = after.split(['/', '?', '#']).next().unwrap_or_default();
    netloc_hostname(netloc)
}

fn is_ip(name: &str) -> bool {
    name.parse::<IpAddr>().is_ok()
}

#[must_use]
pub fn host_allowed(host: &str, trusted: &[String]) -> bool {
    !host.is_empty()
        && (trusted.iter().any(|t| t == host)
            || is_ip(host)
            || host.rsplit_once('.').is_some_and(|(_, tld)| tld == "local"))
}

#[must_use]
pub fn verdict(request: OriginRequest<'_>, trusted: &[String]) -> OriginVerdict {
    let Some(host) = authority_hostname(request.host) else {
        return OriginVerdict::UntrustedHost;
    };
    if !host.is_empty() && !host_allowed(&host, trusted) {
        return OriginVerdict::UntrustedHost;
    }
    let method = if request.method.is_empty() {
        "GET".to_owned()
    } else {
        request.method.to_ascii_uppercase()
    };
    if !UNSAFE.contains(&method.as_str()) {
        return OriginVerdict::Allow;
    }
    if request.fetch_site.eq_ignore_ascii_case("cross-site") {
        return OriginVerdict::CrossSite;
    }
    if !request.origin.is_empty() {
        match origin_hostname(request.origin) {
            Some(name) if name == host => {}
            _ => return OriginVerdict::ForeignOrigin,
        }
    }
    OriginVerdict::Allow
}
