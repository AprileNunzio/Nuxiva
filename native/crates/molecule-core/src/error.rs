use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MolError {
    TooLarge,
    TooManyAtoms,
    LineTooLong(u32),
    BadNumber(u32),
    NotText,
    Empty,
    UnknownFormat,
    MissingColumn,
}

impl MolError {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::TooLarge => "molecule_too_large",
            Self::TooManyAtoms => "molecule_too_many_atoms",
            Self::LineTooLong(_) => "molecule_line_too_long",
            Self::BadNumber(_) => "molecule_bad_number",
            Self::NotText => "molecule_not_text",
            Self::Empty => "molecule_empty",
            Self::UnknownFormat => "molecule_unknown_format",
            Self::MissingColumn => "molecule_missing_column",
        }
    }
}

impl fmt::Display for MolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::LineTooLong(line) | Self::BadNumber(line) => {
                write!(f, "{} at line {line}", self.code())
            }
            _ => f.write_str(self.code()),
        }
    }
}

impl std::error::Error for MolError {}

pub type MolResult<T> = Result<T, MolError>;
