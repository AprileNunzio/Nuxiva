use crate::errors::poisoned;
use nuxiva_chat_core::{
    ChatStudioEngine, IntentTable, MemorySource, Message, Outcome, SmbPathGuard, SmbShareCategory,
    StrictReply,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::{Arc, RwLock};

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustIntents {
    table: IntentTable,
}

#[pymethods]
impl RustIntents {
    #[new]
    fn new() -> PyResult<Self> {
        IntentTable::new()
            .map(|table| Self { table })
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }

    fn detect(&self, py: Python<'_>, text: &str) -> &'static str {
        py.detach(|| self.table.detect(text).name)
    }

    fn names(&self) -> Vec<&'static str> {
        self.table.names().collect()
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustStrictReply {
    inner: StrictReply,
}

#[pymethods]
impl RustStrictReply {
    #[new]
    fn new() -> PyResult<Self> {
        StrictReply::new()
            .map(|inner| Self { inner })
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }

    fn deterministic(&self, py: Python<'_>, text: &str) -> (&'static str, Option<String>) {
        match py.detach(|| self.inner.deterministic(text)) {
            Outcome::Answer(value) => ("answer", Some(value)),
            Outcome::NoAnswer => ("none", None),
            Outcome::Defer => ("defer", None),
        }
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustChatStudio {
    engine: Arc<RwLock<ChatStudioEngine>>,
    smb_guard: SmbPathGuard,
}

#[pymethods]
impl RustChatStudio {
    #[new]
    #[pyo3(signature = (base_smb_dir = "/srv/nuxiva/condivisa"))]
    fn new(base_smb_dir: &str) -> Self {
        Self {
            engine: Arc::new(RwLock::new(ChatStudioEngine::new())),
            smb_guard: SmbPathGuard::new(base_smb_dir),
        }
    }

    fn create_project(
        &self,
        id: String,
        name: String,
        goal: String,
        instructions: String,
        smb_folder: String,
        timestamp_ms: u64,
    ) -> PyResult<String> {
        let mut guard = self.engine.write().map_err(|_| poisoned())?;
        let proj = guard.create_project(id, name, goal, instructions, smb_folder, timestamp_ms);
        serde_json::to_string(&proj).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn create_thread(
        &self,
        id: String,
        project_id: Option<String>,
        title: String,
        model: String,
        timestamp_ms: u64,
    ) -> PyResult<String> {
        let mut guard = self.engine.write().map_err(|_| poisoned())?;
        let thread = guard.create_thread(id, project_id, title, model, timestamp_ms);
        serde_json::to_string(&thread).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn append_message_json(&self, message_json: &str, timestamp_ms: u64) -> PyResult<String> {
        let msg: Message = serde_json::from_str(message_json)
            .map_err(|e| PyValueError::new_err(format!("Invalid message JSON: {e}")))?;
        let mut guard = self.engine.write().map_err(|_| poisoned())?;
        let processed = guard.append_message(msg, timestamp_ms);
        serde_json::to_string(&processed).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn get_messages_json(&self, thread_id: &str) -> PyResult<String> {
        let guard = self.engine.read().map_err(|_| poisoned())?;
        let msgs = guard.get_messages(thread_id);
        serde_json::to_string(&msgs).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn get_threads_json(&self, project_id: Option<&str>) -> PyResult<String> {
        let guard = self.engine.read().map_err(|_| poisoned())?;
        let threads = guard.get_threads(project_id);
        serde_json::to_string(&threads).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn get_projects_json(&self) -> PyResult<String> {
        let guard = self.engine.read().map_err(|_| poisoned())?;
        let projects = guard.get_projects();
        serde_json::to_string(&projects).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn learn_statement(
        &self,
        text: &str,
        source: &str,
        timestamp_ms: u64,
    ) -> PyResult<Option<String>> {
        let src = match source {
            "voice" => MemorySource::VoiceSpeech,
            "smb" => MemorySource::SmbDocument,
            _ => MemorySource::WrittenChat,
        };
        let mut guard = self.engine.write().map_err(|_| poisoned())?;
        let fact = guard.memory_mut().learn_statement(text, src, timestamp_ms);
        match fact {
            Some(f) => serde_json::to_string(&f)
                .map(Some)
                .map_err(|e| PyRuntimeError::new_err(e.to_string())),
            None => Ok(None),
        }
    }

    fn recall_memory_json(&self, query: &str, limit: usize) -> PyResult<String> {
        let mut guard = self.engine.write().map_err(|_| poisoned())?;
        let facts = guard.memory_mut().recall_relevant(query, limit);
        serde_json::to_string(&facts).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    fn build_system_injection(&self, query: &str) -> PyResult<Option<String>> {
        let mut guard = self.engine.write().map_err(|_| poisoned())?;
        Ok(guard.memory_mut().build_system_injection(query))
    }

    fn resolve_safe_smb_path(&self, category: &str, subpath: &str) -> PyResult<String> {
        let cat = SmbShareCategory::from_folder_name(category)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown SMB category: {category}")))?;
        let path = self
            .smb_guard
            .resolve_safe_path(cat, subpath)
            .map_err(|e| PyValueError::new_err(format!("SMB Guard error: {e:?}")))?;
        path.to_str()
            .map(str::to_string)
            .ok_or_else(|| PyValueError::new_err("Invalid UTF-8 in resolved path"))
    }

    #[staticmethod]
    fn format_smb_unc(host: &str, category: &str, subpath: &str) -> PyResult<String> {
        let cat = SmbShareCategory::from_folder_name(category)
            .ok_or_else(|| PyValueError::new_err(format!("Unknown SMB category: {category}")))?;
        Ok(SmbPathGuard::format_unc(host, cat, subpath))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustIntents>()?;
    m.add_class::<RustStrictReply>()?;
    m.add_class::<RustChatStudio>()
}
