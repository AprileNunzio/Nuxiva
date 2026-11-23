use crate::block::Block;
use crate::chain::{Applied, Chain};
use crate::error::{LedgerError, LedgerResult};
use nuxiva_peer_core::{PeerKey, TrustBook};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const MAX_AUTHORS: usize = 256;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Head {
    pub author: String,
    pub index: u64,
    pub hash: String,
}

#[derive(Debug, Clone, Default)]
pub struct Ledger {
    pub(crate) trust: TrustBook,
    pub(crate) chains: BTreeMap<String, Chain>,
    failures: BTreeMap<(String, String), u32>,
}

impl Ledger {
    #[must_use]
    pub fn new(trust: TrustBook) -> Self {
        Self {
            trust,
            chains: BTreeMap::new(),
            failures: BTreeMap::new(),
        }
    }

    #[must_use]
    pub fn trust(&self) -> &TrustBook {
        &self.trust
    }

    pub fn enroll(&mut self, id: &str) -> LedgerResult<()> {
        self.trust.enroll(id)?;
        Ok(())
    }

    pub fn revoke(&mut self, id: &str) -> bool {
        self.chains.remove(id);
        self.failures.retain(|(node, _), _| node != id);
        self.trust.revoke(id)
    }

    pub fn announce(
        &mut self,
        key: &PeerKey,
        addrs: Vec<String>,
        now: i64,
    ) -> LedgerResult<Option<Block>> {
        if !self.trust.trusts(key.id()) {
            return Err(LedgerError::Untrusted);
        }
        let chain = self.chains.entry(key.id().to_owned()).or_default();
        if chain.head().is_some_and(|head| head.addrs == addrs) {
            return Ok(None);
        }
        let ts = chain.head().map_or(now, |head| head.ts.max(now));
        let block = Block::seal(key, chain.next_index(), &chain.next_prev(), ts, addrs)?;
        chain.accept(block.clone(), now)?;
        self.failures.retain(|(node, _), _| node != key.id());
        Ok(Some(block))
    }

    pub fn accept(&mut self, block: Block, now: i64) -> LedgerResult<bool> {
        block.check_shape()?;
        if !self.trust.trusts(&block.author) {
            return Err(LedgerError::Untrusted);
        }
        if !self.chains.contains_key(&block.author) && self.chains.len() >= MAX_AUTHORS {
            return Err(LedgerError::Capacity);
        }
        block.verify()?;
        let author = block.author.clone();
        let chain = self.chains.entry(author.clone()).or_default();
        let applied = chain.accept(block, now);
        if chain.head().is_none() {
            self.chains.remove(&author);
        }
        let applied = applied?;
        if applied == Applied::New {
            self.failures.retain(|(node, _), _| node != &author);
        }
        Ok(applied == Applied::New)
    }

    #[must_use]
    pub fn latest(&self, id: &str) -> Option<&Block> {
        self.chains.get(id).and_then(Chain::head)
    }

    #[must_use]
    pub fn chain(&self, id: &str) -> Option<&Chain> {
        self.chains.get(id)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.chains.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.chains.is_empty()
    }

    #[must_use]
    pub fn candidates(&self, id: &str) -> Vec<String> {
        let Some(head) = self.latest(id) else {
            return Vec::new();
        };
        let mut ranked: Vec<(u32, usize, &String)> = head
            .addrs
            .iter()
            .enumerate()
            .map(|(position, addr)| {
                let fails = self
                    .failures
                    .get(&(id.to_owned(), addr.clone()))
                    .copied()
                    .unwrap_or(0);
                (fails, position, addr)
            })
            .collect();
        ranked.sort();
        ranked
            .into_iter()
            .map(|(_, _, addr)| addr.clone())
            .collect()
    }

    pub fn report_failure(&mut self, id: &str, addr: &str) {
        let slot = self
            .failures
            .entry((id.to_owned(), addr.to_owned()))
            .or_default();
        *slot = slot.saturating_add(1);
    }

    pub fn report_success(&mut self, id: &str, addr: &str) {
        self.failures.remove(&(id.to_owned(), addr.to_owned()));
    }
}
