use std::time::Duration;

use nuxiva_node_core::DeviceKey;
use serde_json::{Value, json};

use super::client::{Link, LinkError, normalize_server};
use super::tls::{fetch_ca, first_contact, pem_fingerprint, verify_server};
use crate::vault::Identity;

const POLL: Duration = Duration::from_secs(3);
const ATTEMPTS: u32 = 300;

#[derive(Debug)]
pub struct Pairing {
    pub server: String,
    pub ca_pem: String,
    pub ca_fingerprint: String,
    pub pinned: bool,
    pub code: String,
    key: DeviceKey,
    node_id: String,
    name: String,
}

#[derive(Debug)]
pub struct Offer<'a> {
    pub server: &'a str,
    pub pin: Option<&'a str>,
    pub node_id: &'a str,
    pub name: &'a str,
    pub kind: &'a str,
    pub room: &'a str,
}

pub fn begin(offer: &Offer) -> Result<Pairing, LinkError> {
    let server = normalize_server(offer.server)?;
    let pinned = offer.pin.is_some();
    let ca_pem = if let Some(pin) = offer.pin {
        first_contact(&server, pin)?
    } else {
        let pem = fetch_ca(&server)?;
        verify_server(&server, &pem)?;
        pem
    };
    let ca_fingerprint = pem_fingerprint(&ca_pem)?;
    let key = DeviceKey::generate().map_err(|_| LinkError::Protocol)?;
    let code = key.pairing_code().map_err(|_| LinkError::Protocol)?;
    let link = Link::anonymous(&server, &ca_pem, Duration::from_secs(30))?;
    let reply = link.post(
        "/api/nodes/request",
        &json!({
            "id": offer.node_id,
            "name": offer.name,
            "type": offer.kind,
            "room": offer.room,
            "pubkey": key.public_hex()
        }),
    )?;
    let echoed = reply.get("fingerprint").and_then(Value::as_str);
    if echoed != Some(code.as_str()) || reply.get("signed").and_then(Value::as_bool) != Some(true) {
        return Err(LinkError::Pin("pairing_code_mismatch"));
    }
    Ok(Pairing {
        server,
        ca_pem,
        ca_fingerprint,
        pinned,
        code,
        key,
        node_id: offer.node_id.to_owned(),
        name: offer.name.to_owned(),
    })
}

impl Pairing {
    pub fn poll(&self) -> Result<Option<Identity>, LinkError> {
        let link = Link::proving(
            &self.server,
            &self.ca_pem,
            &self.node_id,
            &self.key.seed_hex(),
            Duration::from_secs(30),
        )?;
        let reply = link.post("/api/nodes/claim", &json!({"id": self.node_id}))?;
        if reply.get("approved").and_then(Value::as_bool) != Some(true) {
            return Ok(None);
        }
        let token = reply
            .get("token")
            .and_then(Value::as_str)
            .ok_or(LinkError::Protocol)?;
        Ok(Some(Identity {
            server: self.server.clone(),
            node_id: self.node_id.clone(),
            name: self.name.clone(),
            token: token.to_owned(),
            ca_pem: self.ca_pem.clone(),
            secret: self.key.seed_hex().to_string(),
        }))
    }

    pub fn wait(&self) -> Result<Identity, LinkError> {
        for _ in 0..ATTEMPTS {
            std::thread::sleep(POLL);
            match self.poll() {
                Ok(Some(identity)) => return Ok(identity),
                Ok(None) | Err(LinkError::Network(_)) => {}
                Err(error) => return Err(error),
            }
        }
        Err(LinkError::Rejected(408, "pairing_expired".to_owned()))
    }
}
