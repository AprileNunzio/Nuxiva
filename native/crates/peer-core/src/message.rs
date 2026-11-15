use crate::capability::{Capabilities, Load};
use crate::job::JobSpec;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum Message {
    Announce {
        caps: Capabilities,
    },
    Heartbeat {
        load: Load,
    },
    Submit {
        spec: JobSpec,
    },
    Assign {
        job: u64,
        node: String,
        lease_until: i64,
    },
    Progress {
        job: u64,
    },
    Result {
        job: u64,
        ok: bool,
    },
    Leave,
}

impl Message {
    pub fn validate(&self, from: &str) -> crate::error::PeerResult<()> {
        use crate::error::PeerError;
        match self {
            Self::Announce { caps } => caps.validate(),
            Self::Heartbeat { load } => load.validate(),
            Self::Submit { spec } => {
                spec.validate()?;
                if spec.requester == from {
                    Ok(())
                } else {
                    Err(PeerError::Untrusted)
                }
            }
            Self::Assign {
                job,
                node,
                lease_until,
            } => {
                crate::ident::check_id(node)?;
                if *job == 0 || *lease_until < 0 {
                    Err(PeerError::Field)
                } else {
                    Ok(())
                }
            }
            Self::Progress { job } | Self::Result { job, .. } => {
                if *job == 0 {
                    Err(PeerError::Field)
                } else {
                    Ok(())
                }
            }
            Self::Leave => Ok(()),
        }
    }
}
