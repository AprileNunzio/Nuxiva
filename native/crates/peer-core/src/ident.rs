use crate::error::{PeerError, PeerResult};
use nuxiva_node_core::identity::parse_key;

pub const ID_LEN: usize = 64;

pub fn check_id(id: &str) -> PeerResult<()> {
    if id.len() != ID_LEN || !id.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
        return Err(PeerError::Field);
    }
    parse_key(id).map(|_| ()).map_err(|_| PeerError::Key)
}
