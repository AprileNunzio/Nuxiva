use crate::block::Block;
use crate::error::{LedgerError, LedgerResult};
use crate::ledger::{Head, Ledger, MAX_AUTHORS};
use crate::sync::{MAX_SYNC, MergeReport};
use nuxiva_peer_core::ident::check_id;
use serde::{Deserialize, Serialize};

pub const MAX_WIRE: usize = 64 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "t", rename_all = "snake_case", deny_unknown_fields)]
pub enum Wire {
    Want { id: String },
    Have { block: Block },
    Digest { heads: Vec<Head> },
    Delta { blocks: Vec<Block> },
}

impl Wire {
    pub fn encode(&self) -> LedgerResult<Vec<u8>> {
        let bytes = serde_json::to_vec(self).map_err(|_| LedgerError::Field)?;
        if bytes.len() > MAX_WIRE {
            return Err(LedgerError::Limit);
        }
        Ok(bytes)
    }

    pub fn decode(bytes: &[u8]) -> LedgerResult<Self> {
        if bytes.len() > MAX_WIRE {
            return Err(LedgerError::Limit);
        }
        let wire: Self = serde_json::from_slice(bytes).map_err(|_| LedgerError::Field)?;
        wire.check()?;
        Ok(wire)
    }

    fn check(&self) -> LedgerResult<()> {
        match self {
            Self::Want { id } => check_id(id).map_err(LedgerError::from),
            Self::Have { block } => block.check_shape(),
            Self::Digest { heads } if heads.len() > MAX_AUTHORS => Err(LedgerError::Limit),
            Self::Delta { blocks } if blocks.len() > MAX_SYNC => Err(LedgerError::Limit),
            Self::Digest { .. } | Self::Delta { .. } => Ok(()),
        }
    }
}

impl Ledger {
    #[must_use]
    pub fn answer(&self, request: &Wire) -> Option<Wire> {
        match request {
            Wire::Want { id } => self.latest(id).map(|block| Wire::Have {
                block: block.clone(),
            }),
            Wire::Digest { heads } => {
                let blocks = self.missing_for(heads);
                (!blocks.is_empty()).then_some(Wire::Delta { blocks })
            }
            Wire::Have { .. } | Wire::Delta { .. } => None,
        }
    }

    pub fn absorb(&mut self, reply: Wire, now: i64) -> MergeReport {
        match reply {
            Wire::Have { block } => self.merge(vec![block], now),
            Wire::Delta { blocks } => self.merge(blocks, now),
            Wire::Want { .. } | Wire::Digest { .. } => MergeReport::default(),
        }
    }

    #[must_use]
    pub fn digest_request(&self) -> Wire {
        Wire::Digest {
            heads: self.digest(),
        }
    }
}
