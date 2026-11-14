use nuxiva_context_core::{PersonId, Role};

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::Level;
use crate::store::{Knowledge, Partition};

impl Knowledge {
    #[must_use]
    pub fn ceiling(&self, who: &PersonId, target: &Partition) -> Option<Level> {
        let me = self.partitions.get(who)?;
        if !me.consent {
            return None;
        }
        if &target.owner == who {
            return Some(Level::Secret);
        }
        let household = me.role == Role::Family && target.role == Role::Family && target.consent;
        household.then_some(Level::Family)
    }

    pub fn own_mut(&mut self, who: &PersonId) -> KnowledgeResult<&mut Partition> {
        let partition = self
            .partitions
            .get_mut(who)
            .ok_or(KnowledgeError::NotFound)?;
        if partition.consent {
            Ok(partition)
        } else {
            Err(KnowledgeError::Forbidden)
        }
    }

    pub fn own(&self, who: &PersonId) -> KnowledgeResult<&Partition> {
        let partition = self.partition(who)?;
        if partition.consent {
            Ok(partition)
        } else {
            Err(KnowledgeError::Forbidden)
        }
    }

    #[must_use]
    pub fn visible(&self, who: &PersonId, household: bool) -> Vec<(&Partition, Level)> {
        let mut out: Vec<(&Partition, Level)> = self
            .partitions
            .values()
            .filter(|p| household || &p.owner == who)
            .filter_map(|p| self.ceiling(who, p).map(|level| (p, level)))
            .collect();
        out.sort_by(|a, b| a.0.owner.cmp(&b.0.owner));
        out
    }
}
