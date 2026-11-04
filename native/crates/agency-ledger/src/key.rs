use std::fmt;

use zeroize::Zeroizing;

pub struct LedgerKey(Zeroizing<[u8; 32]>);

impl LedgerKey {
    #[must_use]
    pub fn from_bytes(bytes: [u8; 32]) -> Self {
        Self(Zeroizing::new(bytes))
    }

    pub(crate) fn bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl fmt::Debug for LedgerKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("LedgerKey(<redacted>)")
    }
}
