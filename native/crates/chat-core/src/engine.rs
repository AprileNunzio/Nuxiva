use crate::artifact::ArtifactParser;
use crate::memory::CrossMemoryVault;
use crate::types::{Message, Project, Role, Thread};
use std::collections::HashMap;

#[derive(Debug, Clone, Default)]
pub struct ChatStudioEngine {
    projects: HashMap<String, Project>,
    threads: HashMap<String, Thread>,
    messages: HashMap<String, Vec<Message>>,
    memory: CrossMemoryVault,
    artifact_parser: ArtifactParser,
}

impl ChatStudioEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            projects: HashMap::new(),
            threads: HashMap::new(),
            messages: HashMap::new(),
            memory: CrossMemoryVault::new(),
            artifact_parser: ArtifactParser::new(),
        }
    }

    pub fn create_project(
        &mut self,
        id: String,
        name: String,
        goal: String,
        instructions: String,
        smb_folder: String,
        timestamp_ms: u64,
    ) -> Project {
        let project = Project {
            id: id.clone(),
            name,
            goal,
            instructions,
            smb_folder,
            created_at_ms: timestamp_ms,
            updated_at_ms: timestamp_ms,
        };
        self.projects.insert(id, project.clone());
        project
    }

    pub fn create_thread(
        &mut self,
        id: String,
        project_id: Option<String>,
        title: String,
        model: String,
        timestamp_ms: u64,
    ) -> Thread {
        let thread = Thread {
            id: id.clone(),
            project_id,
            title,
            created_at_ms: timestamp_ms,
            updated_at_ms: timestamp_ms,
            model,
            pinned: false,
        };
        self.threads.insert(id, thread.clone());
        thread
    }

    pub fn append_message(&mut self, msg: Message, timestamp_ms: u64) -> Message {
        let thread_id = msg.thread_id.clone();
        if let Some(t) = self.threads.get_mut(&thread_id) {
            t.updated_at_ms = timestamp_ms;
        }

        let mut processed = msg;
        if processed.role == Role::Assistant && processed.artifacts.is_empty() {
            processed.artifacts = self.artifact_parser.extract(&processed.content);
        }

        self.messages
            .entry(thread_id)
            .or_default()
            .push(processed.clone());

        processed
    }

    #[must_use]
    pub fn get_messages(&self, thread_id: &str) -> Vec<Message> {
        self.messages.get(thread_id).cloned().unwrap_or_default()
    }

    #[must_use]
    pub fn get_threads(&self, project_id: Option<&str>) -> Vec<Thread> {
        let mut list: Vec<Thread> = self
            .threads
            .values()
            .filter(|t| match project_id {
                Some(pid) => t.project_id.as_deref() == Some(pid),
                None => true,
            })
            .cloned()
            .collect();
        list.sort_by_key(|a| std::cmp::Reverse(a.updated_at_ms));
        list
    }

    #[must_use]
    pub fn get_projects(&self) -> Vec<Project> {
        let mut list: Vec<Project> = self.projects.values().cloned().collect();
        list.sort_by_key(|a| std::cmp::Reverse(a.updated_at_ms));
        list
    }

    pub fn memory_mut(&mut self) -> &mut CrossMemoryVault {
        &mut self.memory
    }

    #[must_use]
    pub fn memory(&self) -> &CrossMemoryVault {
        &self.memory
    }

    #[must_use]
    pub fn artifact_parser(&self) -> &ArtifactParser {
        &self.artifact_parser
    }
}
