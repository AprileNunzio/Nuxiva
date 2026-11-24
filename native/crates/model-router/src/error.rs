use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum RouteError {
    NoModel,
    OverBudget,
    TooLarge,
    Invalid(&'static str),
}

pub type RouteResult<T> = Result<T, RouteError>;

impl fmt::Display for RouteError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoModel => f.write_str("route.no_model"),
            Self::OverBudget => f.write_str("route.over_budget"),
            Self::TooLarge => f.write_str("route.too_large"),
            Self::Invalid(what) => write!(f, "route.invalid.{what}"),
        }
    }
}

impl std::error::Error for RouteError {}
