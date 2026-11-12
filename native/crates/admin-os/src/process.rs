use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ProcessStatus {
    Running,
    Idle,
    Suspended,
    Terminated,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProcessInfo {
    pub id: String,
    pub name: String,
    pub status: ProcessStatus,
    pub memory_bytes: u64,
    pub cpu_percent: f64,
    pub started_at_secs: u64,
}

#[derive(Debug, Clone)]
pub struct ProcessManager {
    max_processes: usize,
    processes: Vec<ProcessInfo>,
}

impl Default for ProcessManager {
    fn default() -> Self {
        Self {
            max_processes: 256,
            processes: Vec::new(),
        }
    }
}

impl ProcessManager {
    #[must_use]
    pub const fn new(max_processes: usize) -> Self {
        Self {
            max_processes,
            processes: Vec::new(),
        }
    }

    #[must_use]
    pub fn sanitize_id(id: &str) -> Option<String> {
        let trimmed = id.trim();
        if trimmed.is_empty() || trimmed.len() > 64 {
            return None;
        }
        if trimmed.contains("..") || trimmed.contains('/') || trimmed.contains('\\') {
            return None;
        }
        if !trimmed
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-' || c == '.')
        {
            return None;
        }
        Some(trimmed.to_string())
    }

    #[must_use]
    pub fn sanitize_name(name: &str) -> Option<String> {
        let trimmed = name.trim();
        if trimmed.is_empty() || trimmed.len() > 64 {
            return None;
        }
        Some(trimmed.to_string())
    }

    pub fn register(
        &mut self,
        id: &str,
        name: &str,
        memory_bytes: u64,
        cpu_percent: f64,
        started_at_secs: u64,
    ) -> Result<ProcessInfo, &'static str> {
        let safe_id = Self::sanitize_id(id).ok_or("Invalid process id")?;
        let safe_name = Self::sanitize_name(name).ok_or("Invalid process name")?;

        if let Some(existing) = self.processes.iter_mut().find(|p| p.id == safe_id) {
            existing.name = safe_name;
            existing.status = ProcessStatus::Running;
            existing.memory_bytes = memory_bytes;
            existing.cpu_percent = cpu_percent;
            return Ok(existing.clone());
        }

        if self.processes.len() >= self.max_processes {
            return Err("Process table capacity reached");
        }

        let info = ProcessInfo {
            id: safe_id,
            name: safe_name,
            status: ProcessStatus::Running,
            memory_bytes,
            cpu_percent,
            started_at_secs,
        };

        self.processes.push(info.clone());
        Ok(info)
    }

    pub fn terminate(&mut self, id: &str) -> bool {
        if let Some(proc_info) = self.processes.iter_mut().find(|p| p.id == id) {
            proc_info.status = ProcessStatus::Terminated;
            proc_info.cpu_percent = 0.0;
            return true;
        }
        false
    }

    pub fn remove(&mut self, id: &str) -> bool {
        let initial_len = self.processes.len();
        self.processes.retain(|p| p.id != id);
        self.processes.len() < initial_len
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&ProcessInfo> {
        self.processes.iter().find(|p| p.id == id)
    }

    #[must_use]
    pub fn list_active(&self) -> Vec<ProcessInfo> {
        self.processes
            .iter()
            .filter(|p| p.status != ProcessStatus::Terminated)
            .cloned()
            .collect()
    }

    #[must_use]
    pub fn count_active(&self) -> usize {
        self.processes
            .iter()
            .filter(|p| p.status != ProcessStatus::Terminated)
            .count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn process_registration_and_termination() {
        let mut mgr = ProcessManager::default();
        let res = mgr.register("svc_brain", "Neural Cortex", 1024, 5.5, 100);
        assert!(res.is_ok());

        assert_eq!(mgr.count_active(), 1);
        let proc_info = mgr.get("svc_brain");
        assert!(proc_info.is_some());

        assert!(mgr.terminate("svc_brain"));
        assert_eq!(mgr.count_active(), 0);
    }

    #[test]
    fn rejects_malicious_process_ids() {
        let mut mgr = ProcessManager::default();
        assert!(mgr.register("../etc/passwd", "Bad", 0, 0.0, 0).is_err());
        assert!(mgr.register("name with spaces", "Bad", 0, 0.0, 0).is_err());
        assert!(mgr.register("", "Bad", 0, 0.0, 0).is_err());
    }

    #[test]
    fn enforces_capacity_limit() {
        let mut mgr = ProcessManager::new(2);
        assert!(mgr.register("p1", "Proc 1", 10, 1.0, 1).is_ok());
        assert!(mgr.register("p2", "Proc 2", 20, 2.0, 2).is_ok());
        assert!(mgr.register("p3", "Proc 3", 30, 3.0, 3).is_err());
    }
}
