use crate::error::TernaryError;
use crate::vector::TernaryVector;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TernaryRecord {
    pub id: String,
    pub vector: TernaryVector,
    pub project_id: Option<String>,
    pub timestamp_ms: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TernaryIndex {
    dim: usize,
    records: Vec<TernaryRecord>,
}

impl TernaryIndex {
    pub fn new(dim: usize) -> Result<Self, TernaryError> {
        if dim == 0 {
            return Err(TernaryError::EmptyVector);
        }
        Ok(Self {
            dim,
            records: Vec::new(),
        })
    }

    #[must_use]
    pub fn dim(&self) -> usize {
        self.dim
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.records.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    pub fn add(&mut self, record: TernaryRecord) -> Result<(), TernaryError> {
        if record.vector.dim() != self.dim {
            return Err(TernaryError::DimensionMismatch {
                expected: self.dim,
                actual: record.vector.dim(),
            });
        }
        self.records.push(record);
        Ok(())
    }

    pub fn search_top_k(
        &self,
        query: &TernaryVector,
        k: usize,
    ) -> Result<Vec<(String, i32)>, TernaryError> {
        if query.dim() != self.dim {
            return Err(TernaryError::DimensionMismatch {
                expected: self.dim,
                actual: query.dim(),
            });
        }
        let mut scored: Vec<(String, i32)> = Vec::with_capacity(self.records.len());
        for rec in &self.records {
            let score = query.dot(&rec.vector)?;
            scored.push((rec.id.clone(), score));
        }
        scored.sort_by_key(|item| std::cmp::Reverse(item.1));
        scored.truncate(k);
        Ok(scored)
    }

    #[must_use]
    pub fn filter_by_project(&self, project_id: &str) -> Vec<&TernaryRecord> {
        self.records
            .iter()
            .filter(|r| r.project_id.as_deref() == Some(project_id))
            .collect()
    }
}
