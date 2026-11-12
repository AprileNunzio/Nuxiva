use std::sync::Arc;
use std::time::Duration;

use sha2::{Digest, Sha256};
use subtle::ConstantTimeEq;
use ureq::Agent;
use ureq::tls::{Certificate, PemItem, RootCerts, TlsConfig, parse_pem};

use super::client::LinkError;

const CA_PATH: &str = "/nuxiva-ca.crt";
const CA_LIMIT: u64 = 64 * 1024;
const USER_AGENT: &str = concat!("nuxiva-satellite/", env!("CARGO_PKG_VERSION"));

pub fn certificates(pem: &str) -> Result<Vec<Certificate<'static>>, LinkError> {
    let certs: Vec<Certificate<'static>> = parse_pem(pem.as_bytes())
        .filter_map(|item| match item {
            Ok(PemItem::Certificate(cert)) => Some(cert),
            _ => None,
        })
        .collect();
    if certs.is_empty() {
        return Err(LinkError::Pin("ca_invalid"));
    }
    Ok(certs)
}

pub fn pem_fingerprint(pem: &str) -> Result<String, LinkError> {
    let certs = certificates(pem)?;
    let first = certs.first().ok_or(LinkError::Pin("ca_invalid"))?;
    Ok(hex(&Sha256::digest(first.der())))
}

fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    bytes
        .iter()
        .fold(String::with_capacity(64), |mut out, byte| {
            let _ = write!(out, "{byte:02x}");
            out
        })
}

fn agent(tls: TlsConfig, timeout: Duration) -> Agent {
    Agent::config_builder()
        .tls_config(tls)
        .https_only(true)
        .http_status_as_error(false)
        .max_redirects(0)
        .timeout_global(Some(timeout))
        .user_agent(USER_AGENT)
        .build()
        .into()
}

pub fn pinned_agent(ca_pem: &str, timeout: Duration) -> Result<Agent, LinkError> {
    let roots = RootCerts::Specific(Arc::new(certificates(ca_pem)?));
    Ok(agent(
        TlsConfig::builder().root_certs(roots).build(),
        timeout,
    ))
}

pub fn first_contact(server: &str, pin: &str) -> Result<String, LinkError> {
    let blind = agent(
        TlsConfig::builder().disable_verification(true).build(),
        Duration::from_secs(10),
    );
    let url = format!("{server}{CA_PATH}");
    let mut response = blind.get(&url).call().map_err(|e| LinkError::network(&e))?;
    if response.status().as_u16() != 200 {
        return Err(LinkError::Pin("ca_unavailable"));
    }
    let pem = response
        .body_mut()
        .with_config()
        .limit(CA_LIMIT)
        .read_to_string()
        .map_err(|e| LinkError::network(&e))?;
    let fingerprint = pem_fingerprint(&pem)?;
    if !bool::from(fingerprint.as_bytes().ct_eq(pin.as_bytes())) {
        return Err(LinkError::Pin("pin_mismatch"));
    }
    let pinned = pinned_agent(&pem, Duration::from_secs(10))?;
    pinned
        .get(&url)
        .call()
        .map_err(|_| LinkError::Pin("server_not_signed_by_ca"))?;
    Ok(pem)
}
