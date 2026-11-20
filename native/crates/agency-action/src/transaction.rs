use crate::error::ActionError;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransactionStatus {
    Active,
    Committed,
    RolledBack,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileSnapshot {
    pub original_content: Option<String>,
    pub timestamp_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActionTransaction {
    id: String,
    status: TransactionStatus,
    snapshots: BTreeMap<String, FileSnapshot>,
}

impl ActionTransaction {
    #[must_use]
    pub fn new(id: String) -> Self {
        Self {
            id,
            status: TransactionStatus::Active,
            snapshots: BTreeMap::new(),
        }
    }

    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    #[must_use]
    pub fn status(&self) -> TransactionStatus {
        self.status
    }

    #[must_use]
    pub fn is_active(&self) -> bool {
        self.status == TransactionStatus::Active
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.snapshots.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.snapshots.is_empty()
    }

    pub fn record_snapshot(
        &mut self,
        path: String,
        original_content: Option<String>,
        timestamp_ms: u64,
    ) -> Result<(), ActionError> {
        if self.status != TransactionStatus::Active {
            return Err(ActionError::InvalidPath(format!(
                "transaction {} is no longer active",
                self.id
            )));
        }
        let trimmed = path.trim();
        if trimmed.is_empty()
            || trimmed.contains("..")
            || trimmed.starts_with('/')
            || trimmed.starts_with('\\')
        {
            return Err(ActionError::InvalidPath(path));
        }

        if !self.snapshots.contains_key(trimmed) {
            self.snapshots.insert(
                trimmed.to_string(),
                FileSnapshot {
                    original_content,
                    timestamp_ms,
                },
            );
        }
        Ok(())
    }

    pub fn commit(&mut self) -> Result<usize, ActionError> {
        if self.status != TransactionStatus::Active {
            return Err(ActionError::InvalidPath(format!(
                "cannot commit inactive transaction {}",
                self.id
            )));
        }
        let count = self.snapshots.len();
        self.status = TransactionStatus::Committed;
        Ok(count)
    }

    pub fn rollback(&mut self) -> Result<BTreeMap<String, Option<String>>, ActionError> {
        if self.status != TransactionStatus::Active {
            return Err(ActionError::InvalidPath(format!(
                "cannot rollback inactive transaction {}",
                self.id
            )));
        }
        self.status = TransactionStatus::RolledBack;
        let mut restores = BTreeMap::new();
        for (path, snapshot) in &self.snapshots {
            restores.insert(path.clone(), snapshot.original_content.clone());
        }
        Ok(restores)
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::panic)]
mod tests {
    use super::*;

    #[test]
    fn test_transaction_lifecycle_commit() {
        let mut tx = ActionTransaction::new("tx_01".into());
        assert!(tx.is_active());
        assert_eq!(tx.len(), 0);

        let res = tx.record_snapshot("src/lib.rs".into(), Some("fn init() {}".into()), 100);
        assert!(res.is_ok());
        assert_eq!(tx.len(), 1);

        let committed = tx.commit().unwrap();
        assert_eq!(committed, 1);
        assert_eq!(tx.status(), TransactionStatus::Committed);
        assert!(!tx.is_active());

        assert!(
            tx.record_snapshot("src/other.rs".into(), None, 200)
                .is_err()
        );
    }

    #[test]
    fn test_transaction_rollback_returns_original_snapshots() {
        let mut tx = ActionTransaction::new("tx_02".into());
        tx.record_snapshot("config.json".into(), Some("{\"v\":1}".into()), 100)
            .unwrap();
        tx.record_snapshot("new_file.txt".into(), None, 101)
            .unwrap();

        tx.record_snapshot("config.json".into(), Some("{\"v\":2}".into()), 102)
            .unwrap();

        let restored = tx.rollback().unwrap();
        assert_eq!(tx.status(), TransactionStatus::RolledBack);
        assert_eq!(
            restored.get("config.json").unwrap(),
            &Some("{\"v\":1}".to_string())
        );
        assert_eq!(restored.get("new_file.txt").unwrap(), &None);
    }

    #[test]
    fn test_transaction_rejects_invalid_path() {
        let mut tx = ActionTransaction::new("tx_03".into());
        assert!(
            tx.record_snapshot("../etc/passwd".into(), None, 100)
                .is_err()
        );
        assert!(
            tx.record_snapshot("/root/secret".into(), None, 100)
                .is_err()
        );
        assert!(tx.record_snapshot(String::new(), None, 100).is_err());
    }
}
