use crate::capability::Capability;
use crate::cell::Cell;
use crate::matrix::Matrix;
use crate::role::Role;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Strength {
    None,
    Weak,
    Single,
    Strong,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Request<'a> {
    pub capabilities: &'a [Capability],
    pub role: Role,
    pub strength: Strength,
    pub local: Option<bool>,
    pub own: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "verdict", content = "detail", rename_all = "snake_case")]
pub enum Verdict {
    Allow,
    Confirm,
    NeedProof(Strength),
    Deny(&'static str),
}

const fn rank(verdict: Verdict) -> u8 {
    match verdict {
        Verdict::Allow => 0,
        Verdict::Confirm => 1,
        Verdict::NeedProof(_) => 2,
        Verdict::Deny(_) => 3,
    }
}

fn single(cell: Cell, req: &Request<'_>) -> Verdict {
    match cell {
        Cell::Allow => Verdict::Allow,
        Cell::Room => match req.local {
            Some(false) => Verdict::Deny("room"),
            _ => Verdict::Allow,
        },
        Cell::Own => {
            if req.own {
                Verdict::Allow
            } else {
                Verdict::Deny("owner_data")
            }
        }
        Cell::Confirm => {
            if req.strength >= Strength::Single {
                Verdict::Confirm
            } else {
                Verdict::NeedProof(Strength::Single)
            }
        }
        Cell::Strong => {
            if req.strength >= Strength::Strong {
                Verdict::Allow
            } else {
                Verdict::NeedProof(Strength::Strong)
            }
        }
        Cell::Deny => Verdict::Deny(if req.role.outsider() { "guest" } else { "role" }),
    }
}

#[must_use]
pub fn decide(req: &Request<'_>, matrix: &Matrix) -> Verdict {
    if req.capabilities.is_empty() {
        return single(Cell::Deny, req);
    }
    req.capabilities
        .iter()
        .map(|cap| single(matrix.cell(cap, req.role), req))
        .max_by_key(|v| rank(*v))
        .unwrap_or(Verdict::Deny("role"))
}
