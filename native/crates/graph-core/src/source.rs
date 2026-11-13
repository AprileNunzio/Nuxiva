use std::collections::BTreeMap;

use crate::error::{GraphError, GraphResult};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub path: String,
    pub size: u64,
}

pub trait FileSource {
    fn list(&self) -> GraphResult<Vec<Entry>>;
    fn read(&self, path: &str, limit: usize) -> GraphResult<Vec<u8>>;
}

#[derive(Debug, Clone, Default)]
pub struct MemorySource {
    files: BTreeMap<String, Vec<u8>>,
}

impl MemorySource {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn put(&mut self, path: &str, content: &str) {
        self.files
            .insert(path.to_owned(), content.as_bytes().to_vec());
    }

    pub fn put_bytes(&mut self, path: &str, content: Vec<u8>) {
        self.files.insert(path.to_owned(), content);
    }

    pub fn remove(&mut self, path: &str) {
        self.files.remove(path);
    }
}

impl FileSource for MemorySource {
    fn list(&self) -> GraphResult<Vec<Entry>> {
        Ok(self
            .files
            .iter()
            .map(|(path, body)| Entry {
                path: path.clone(),
                size: body.len() as u64,
            })
            .collect())
    }

    fn read(&self, path: &str, limit: usize) -> GraphResult<Vec<u8>> {
        let body = self.files.get(path).ok_or(GraphError::Source)?;
        if body.len() > limit {
            return Err(GraphError::TooLarge);
        }
        Ok(body.clone())
    }
}
