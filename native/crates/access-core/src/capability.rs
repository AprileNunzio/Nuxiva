use crate::error::AccessError;

pub const MAX_SEGMENT: usize = 32;

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Capability(String);

fn segment(raw: &str) -> bool {
    !raw.is_empty()
        && raw.len() <= MAX_SEGMENT
        && raw.bytes().all(|b| b.is_ascii_lowercase() || b == b'_')
}

impl Capability {
    pub fn parse(raw: &str) -> Result<Self, AccessError> {
        let parts: Vec<&str> = raw.split('.').collect();
        if !(2..=3).contains(&parts.len()) || !parts.iter().all(|p| segment(p)) {
            return Err(AccessError::Capability);
        }
        Ok(Self(raw.to_owned()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    #[must_use]
    pub fn domain(&self) -> &str {
        self.0.split('.').next().unwrap_or_default()
    }

    #[must_use]
    pub fn candidates(&self) -> Vec<String> {
        let parts: Vec<&str> = self.0.split('.').collect();
        let mut out = vec![self.0.clone()];
        let mut prefix = parts.clone();
        while prefix.len() > 1 {
            prefix.pop();
            out.push(format!("{}.*", prefix.join(".")));
        }
        out
    }
}
