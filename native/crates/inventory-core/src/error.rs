use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum InventoryError {
    Invalid(&'static str),
    Unknown(String),
    Stale(String),
    Scan(String),
}

pub type InventoryResult<T> = Result<T, InventoryError>;

impl fmt::Display for InventoryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "inventory.invalid.{what}"),
            Self::Unknown(id) => write!(f, "inventory.unknown.{id}"),
            Self::Stale(id) => write!(f, "inventory.stale.{id}"),
            Self::Scan(what) => write!(f, "inventory.scan.{what}"),
        }
    }
}

impl std::error::Error for InventoryError {}
