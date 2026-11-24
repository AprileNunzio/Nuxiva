use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum DossierError {
    Invalid(&'static str),
    Missing(String),
    NotApproved,
    RoleDenied,
    Unknown(String),
}

pub type DossierResult<T> = Result<T, DossierError>;

impl fmt::Display for DossierError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "dossier.invalid.{what}"),
            Self::Missing(name) => write!(f, "dossier.missing.{name}"),
            Self::NotApproved => f.write_str("dossier.not_approved"),
            Self::RoleDenied => f.write_str("dossier.role_denied"),
            Self::Unknown(name) => write!(f, "dossier.unknown.{name}"),
        }
    }
}

impl std::error::Error for DossierError {}
