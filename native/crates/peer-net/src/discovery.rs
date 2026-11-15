use crate::beacon::decode;
use crate::throttle::Throttle;
use nuxiva_peer_core::{Directory, PeerError, PeerResult, Verifier};
use std::net::SocketAddr;

#[derive(Debug)]
pub struct Discovery {
    pub directory: Directory,
    verifier: Verifier,
    throttle: Throttle,
}

impl Discovery {
    #[must_use]
    pub fn new(verifier: Verifier) -> Self {
        Self {
            directory: Directory::new(),
            verifier,
            throttle: Throttle::new(8, 1_000),
        }
    }

    pub fn on_datagram(&mut self, bytes: &[u8], from: SocketAddr, now: i64) -> PeerResult<bool> {
        if !self.throttle.allow(from.ip(), now) {
            return Err(PeerError::Limit);
        }
        let envelope = decode(bytes)?;
        self.directory.learn(&self.verifier, &envelope, now)
    }
}
