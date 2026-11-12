use hkdf::Hkdf;
use serde::Serialize;
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::error::MemoryError;
use crate::sighting::{Class, Sighting, Who};

pub const TOKEN_LEN: usize = 16;
pub const MAX_TOKENS: usize = 32;
const INFO: &[u8] = b"nuxiva.memory.index.v1";

pub type Token = [u8; TOKEN_LEN];

pub struct IndexKey(Zeroizing<[u8; 32]>);

impl std::fmt::Debug for IndexKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("IndexKey(..)")
    }
}

fn name<T: Serialize>(value: &T) -> String {
    serde_json::to_value(value)
        .ok()
        .and_then(|v| v.as_str().map(str::to_owned))
        .unwrap_or_default()
}

impl IndexKey {
    pub fn derive(master: &[u8]) -> Result<Self, MemoryError> {
        if master.len() != 32 || master.iter().all(|b| *b == 0) {
            return Err(MemoryError::InvalidKey);
        }
        let mut okm = Zeroizing::new([0_u8; 32]);
        Hkdf::<Sha256>::new(None, master)
            .expand(INFO, &mut *okm)
            .map_err(|_| MemoryError::InvalidKey)?;
        Ok(Self(okm))
    }

    #[must_use]
    pub fn token(&self, field: &str, value: &str) -> Token {
        let mut h = blake3::Hasher::new_keyed(&self.0);
        h.update(field.as_bytes());
        h.update(b"|");
        h.update(value.as_bytes());
        let mut out = [0_u8; TOKEN_LEN];
        out.copy_from_slice(
            h.finalize()
                .as_bytes()
                .get(..TOKEN_LEN)
                .unwrap_or(&[0; TOKEN_LEN]),
        );
        out
    }

    #[must_use]
    pub fn class(&self, class: Class) -> Token {
        self.token("class", &name(&class))
    }

    #[must_use]
    pub fn who(&self, who: &Who) -> Token {
        self.token("who", &who.key())
    }

    #[must_use]
    pub fn of(&self, s: &Sighting) -> Vec<Token> {
        let mut out = vec![
            self.class(s.class),
            self.who(&s.who),
            self.token("camera", &s.camera),
        ];
        if let Some(zone) = &s.zone {
            out.push(self.token("zone", zone));
        }
        let look = &s.look;
        if let Some(c) = look.upper {
            out.push(self.token("upper", &name(&c)));
        }
        if let Some(c) = look.lower {
            out.push(self.token("lower", &name(&c)));
        }
        if let Some(h) = look.headwear {
            out.push(self.token("headwear", &name(&h)));
        }
        if look.face_covered == Some(true) {
            out.push(self.token("face_covered", "1"));
        }
        if look.hi_vis == Some(true) {
            out.push(self.token("hi_vis", "1"));
        }
        for item in &look.carrying {
            out.push(self.token("item", &name(item)));
        }
        if let Some(v) = &s.vehicle {
            out.push(self.token("vehicle", &name(&v.kind)));
            if let Some(c) = v.color {
                out.push(self.token("vehicle_color", &name(&c)));
            }
        }
        out.sort_unstable();
        out.dedup();
        out.truncate(MAX_TOKENS);
        out
    }
}
