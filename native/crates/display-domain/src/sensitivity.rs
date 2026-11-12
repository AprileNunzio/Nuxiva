use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Sensitivity {
    Public,
    Household,
    Personal,
    Sensitive,
}

impl Sensitivity {
    #[must_use]
    pub fn parse(raw: &str) -> Option<Self> {
        match raw {
            "public" => Some(Self::Public),
            "household" => Some(Self::Household),
            "personal" => Some(Self::Personal),
            "sensitive" => Some(Self::Sensitive),
            _ => None,
        }
    }
}
