use std::fmt;

use zeroize::Zeroizing;

use crate::error::{StudioError, StudioResult};

const MIN_LEN: usize = 16;
const MAX_LEN: usize = 256;

pub struct ApiKey(Zeroizing<String>);

impl ApiKey {
    pub fn new(raw: &str) -> StudioResult<Self> {
        let value = raw.trim();
        let valid = (MIN_LEN..=MAX_LEN).contains(&value.len())
            && value
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'));
        if !valid {
            return Err(StudioError::Invalid("api_key"));
        }
        Ok(Self(Zeroizing::new(value.to_owned())))
    }

    pub(crate) fn expose(&self) -> &str {
        self.0.as_str()
    }
}

impl fmt::Debug for ApiKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("ApiKey(***)")
    }
}
