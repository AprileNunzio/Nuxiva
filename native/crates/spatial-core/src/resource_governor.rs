use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ComputeProvider {
    OllamaLocal,
    OllamaRemote,
    ApiKey,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum LocalEngineAction {
    Hibernate,
    KeepActive,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TargetAllocation {
    pub target_id: String,
    pub provider: ComputeProvider,
    pub model_name: String,
    pub node_url: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResourcePlan {
    pub local_engine_action: LocalEngineAction,
    pub local_targets_count: usize,
    pub remote_targets_count: usize,
    pub cloud_targets_count: usize,
    pub active_remote_urls: Vec<String>,
    pub dormant_remote_urls: Vec<String>,
    pub reason_code: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RemoteServerEntry {
    pub id: String,
    pub raw_host: String,
    pub normalized_url: String,
    pub is_online: bool,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct ResourceGovernor {
    targets: Vec<TargetAllocation>,
    remote_servers: Vec<RemoteServerEntry>,
}

impl ResourceGovernor {
    #[must_use]
    pub fn new() -> Self {
        Self {
            targets: Vec::new(),
            remote_servers: Vec::new(),
        }
    }

    #[must_use]
    pub fn normalize_ollama_url(raw: &str) -> String {
        let trimmed = raw.trim().trim_end_matches('/');
        if trimmed.is_empty() {
            return "http://127.0.0.1:11434".to_string();
        }

        let with_scheme = if trimmed.starts_with("http://") || trimmed.starts_with("https://") {
            trimmed.to_string()
        } else {
            format!("http://{trimmed}")
        };

        if let Some(idx) = with_scheme.find("://") {
            let scheme_end = idx.saturating_add(3);
            if let Some(rest) = with_scheme.get(scheme_end..) {
                let host_part = rest.split('/').next().unwrap_or(rest);
                if !host_part.contains(':') {
                    return format!("{with_scheme}:11434");
                }
            }
        }

        with_scheme
    }

    pub fn set_target_allocation(&mut self, alloc: TargetAllocation) {
        if let Some(existing) = self
            .targets
            .iter_mut()
            .find(|t| t.target_id == alloc.target_id)
        {
            *existing = alloc;
        } else {
            self.targets.push(alloc);
        }
    }

    pub fn register_remote_server(&mut self, id: impl Into<String>, raw_host: impl Into<String>) {
        let id_str = id.into();
        let raw_str = raw_host.into();
        let normalized = Self::normalize_ollama_url(&raw_str);

        if let Some(existing) = self.remote_servers.iter_mut().find(|s| s.id == id_str) {
            existing.raw_host = raw_str;
            existing.normalized_url = normalized;
        } else {
            self.remote_servers.push(RemoteServerEntry {
                id: id_str,
                raw_host: raw_str,
                normalized_url: normalized,
                is_online: false,
            });
        }
    }

    pub fn set_remote_server_status(&mut self, id: &str, is_online: bool) {
        if let Some(server) = self.remote_servers.iter_mut().find(|s| s.id == id) {
            server.is_online = is_online;
        }
    }

    pub fn apply_global_default_to_all(
        &mut self,
        provider: ComputeProvider,
        model_name: impl Into<String>,
        node_url: Option<&str>,
    ) {
        let m_str = model_name.into();
        let norm_url = node_url.map(Self::normalize_ollama_url);

        for target in &mut self.targets {
            target.provider = provider;
            target.model_name.clone_from(&m_str);
            target.node_url.clone_from(&norm_url);
        }
    }

    #[must_use]
    pub fn evaluate_resource_plan(&self) -> ResourcePlan {
        let mut local_count = 0_usize;
        let mut remote_count = 0_usize;
        let mut cloud_count = 0_usize;
        let mut active_remotes: Vec<String> = Vec::new();

        for t in &self.targets {
            match t.provider {
                ComputeProvider::OllamaLocal => {
                    local_count = local_count.saturating_add(1);
                }
                ComputeProvider::OllamaRemote => {
                    remote_count = remote_count.saturating_add(1);
                    if let Some(ref url) = t.node_url {
                        if !active_remotes.contains(url) {
                            active_remotes.push(url.clone());
                        }
                    }
                }
                ComputeProvider::ApiKey => {
                    cloud_count = cloud_count.saturating_add(1);
                }
            }
        }

        let mut dormant_remotes: Vec<String> = Vec::new();
        for s in &self.remote_servers {
            if !active_remotes.contains(&s.normalized_url) {
                dormant_remotes.push(s.normalized_url.clone());
            }
        }

        if local_count == 0 {
            ResourcePlan {
                local_engine_action: LocalEngineAction::Hibernate,
                local_targets_count: 0,
                remote_targets_count: remote_count,
                cloud_targets_count: cloud_count,
                active_remote_urls: active_remotes,
                dormant_remote_urls: dormant_remotes,
                reason_code: "resource.hibernate_zero_local_targets".to_string(),
            }
        } else {
            ResourcePlan {
                local_engine_action: LocalEngineAction::KeepActive,
                local_targets_count: local_count,
                remote_targets_count: remote_count,
                cloud_targets_count: cloud_count,
                active_remote_urls: active_remotes,
                dormant_remote_urls: dormant_remotes,
                reason_code: "resource.active_local_workload".to_string(),
            }
        }
    }

    #[must_use]
    pub fn targets_len(&self) -> usize {
        self.targets.len()
    }
}
