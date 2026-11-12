use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeComponent {
    pub id: String,
    pub name_key: String,
    pub category: String,
    pub enabled: bool,
    pub cpu_percent: f32,
    pub ram_mb: f32,
    pub gpu_percent: f32,
    pub vram_mb: f32,
    pub delegable: bool,
    pub delegated_to: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeProfile {
    pub node_id: String,
    pub node_name: String,
    pub total_cpu_cores: u32,
    pub total_ram_mb: f32,
    pub has_gpu: bool,
    pub gpu_name: Option<String>,
    pub total_vram_mb: f32,
    pub components: Vec<NodeComponent>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TechnicalEvaluation {
    pub overall_status: String,
    pub total_cpu_percent: f32,
    pub total_ram_used_mb: f32,
    pub total_vram_used_mb: f32,
    pub recommendations: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MeshDispatchResolution {
    pub capability: String,
    pub assigned_node_id: String,
    pub assigned_node_name: String,
    pub is_local: bool,
    pub reason_code: String,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct MeshTaskGovernor {
    nodes: HashMap<String, NodeProfile>,
}

impl MeshTaskGovernor {
    #[must_use]
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
        }
    }

    pub fn register_or_update_node(&mut self, profile: NodeProfile) {
        self.nodes.insert(profile.node_id.clone(), profile);
    }

    #[must_use]
    pub fn get_node(&self, node_id: &str) -> Option<&NodeProfile> {
        self.nodes.get(node_id)
    }

    pub fn toggle_component(&mut self, node_id: &str, component_id: &str, enabled: bool) -> bool {
        let Some(node) = self.nodes.get_mut(node_id) else {
            return false;
        };

        let mut found = false;
        for comp in &mut node.components {
            if comp.id == component_id {
                comp.enabled = enabled;
                if enabled {
                    comp.delegated_to = None;
                }
                found = true;
                break;
            }
        }

        if !found {
            return false;
        }

        self.recompute_delegations();
        true
    }

    pub fn recompute_delegations(&mut self) {
        let node_keys: Vec<String> = self.nodes.keys().cloned().collect();

        for req_id in &node_keys {
            let mut updates: Vec<(String, Option<String>)> = Vec::new();

            if let Some(req_node) = self.nodes.get(req_id) {
                for comp in &req_node.components {
                    if !comp.enabled && comp.delegable {
                        let mut best_target: Option<String> = None;
                        let mut lowest_load = f32::MAX;

                        for (cand_id, cand_node) in &self.nodes {
                            if cand_id == req_id {
                                continue;
                            }
                            let has_active_comp = cand_node
                                .components
                                .iter()
                                .any(|c| c.id == comp.id && c.enabled);
                            if has_active_comp {
                                let cand_load: f32 = cand_node
                                    .components
                                    .iter()
                                    .filter(|c| c.enabled)
                                    .map(|c| c.cpu_percent + c.gpu_percent)
                                    .sum();
                                if cand_load < lowest_load {
                                    lowest_load = cand_load;
                                    best_target = Some(cand_id.clone());
                                }
                            }
                        }
                        updates.push((comp.id.clone(), best_target));
                    }
                }
            }

            if let Some(target_node) = self.nodes.get_mut(req_id) {
                for (comp_id, delegated_target) in updates {
                    if let Some(c) = target_node.components.iter_mut().find(|c| c.id == comp_id) {
                        c.delegated_to = delegated_target;
                    }
                }
            }
        }
    }

    #[must_use]
    pub fn evaluate_node(&self, node_id: &str) -> Option<TechnicalEvaluation> {
        let node = self.nodes.get(node_id)?;

        let mut total_cpu = 0.0f32;
        let mut total_ram = 0.0f32;
        let mut total_vram = 0.0f32;
        let mut has_voice_enabled = false;

        for comp in &node.components {
            if comp.enabled {
                total_cpu += comp.cpu_percent;
                total_ram += comp.ram_mb;
                total_vram += comp.vram_mb;
                if comp.id == "voice_studio" {
                    has_voice_enabled = true;
                }
            }
        }

        let mut recommendations = Vec::new();
        let ram_ratio = if node.total_ram_mb > 0.0 {
            total_ram / node.total_ram_mb
        } else {
            0.0
        };

        if ram_ratio > 0.85 {
            recommendations.push("rec_high_ram_usage".to_string());
            recommendations.push("rec_offload_indexing".to_string());
        }

        if total_cpu > 80.0 {
            recommendations.push("rec_high_cpu_usage".to_string());
            if !node.has_gpu {
                recommendations.push("rec_offload_voice_studio".to_string());
            }
        }

        if node.has_gpu && has_voice_enabled {
            recommendations.push("rec_mesh_voice_host_active".to_string());
        }

        if recommendations.is_empty() {
            recommendations.push("rec_optimal_running".to_string());
        }

        let overall_status = if total_cpu > 85.0 || ram_ratio > 0.90 {
            "critical".to_string()
        } else if total_cpu > 65.0 || ram_ratio > 0.75 {
            "high_load".to_string()
        } else if total_cpu > 40.0 || ram_ratio > 0.50 {
            "moderate_load".to_string()
        } else {
            "optimal".to_string()
        };

        Some(TechnicalEvaluation {
            overall_status,
            total_cpu_percent: total_cpu,
            total_ram_used_mb: total_ram,
            total_vram_used_mb: total_vram,
            recommendations,
        })
    }

    #[must_use]
    pub fn resolve_capability_dispatch(
        &self,
        requesting_node_id: &str,
        capability: &str,
    ) -> MeshDispatchResolution {
        if let Some(req_node) = self.nodes.get(requesting_node_id) {
            let is_enabled_locally = req_node
                .components
                .iter()
                .any(|c| c.id == capability && c.enabled);
            if is_enabled_locally {
                return MeshDispatchResolution {
                    capability: capability.to_string(),
                    assigned_node_id: req_node.node_id.clone(),
                    assigned_node_name: req_node.node_name.clone(),
                    is_local: true,
                    reason_code: "mesh_dispatch_local".to_string(),
                };
            }
        }

        let mut best_node: Option<&NodeProfile> = None;
        let mut lowest_load = f32::MAX;

        for (cand_id, cand_node) in &self.nodes {
            if cand_id == requesting_node_id {
                continue;
            }
            let is_active = cand_node
                .components
                .iter()
                .any(|c| c.id == capability && c.enabled);
            if is_active {
                let load: f32 = cand_node
                    .components
                    .iter()
                    .filter(|c| c.enabled)
                    .map(|c| c.cpu_percent + c.gpu_percent)
                    .sum();
                if load < lowest_load {
                    lowest_load = load;
                    best_node = Some(cand_node);
                }
            }
        }

        if let Some(winner) = best_node {
            MeshDispatchResolution {
                capability: capability.to_string(),
                assigned_node_id: winner.node_id.clone(),
                assigned_node_name: winner.node_name.clone(),
                is_local: false,
                reason_code: "mesh_dispatch_delegated_peer".to_string(),
            }
        } else {
            MeshDispatchResolution {
                capability: capability.to_string(),
                assigned_node_id: String::new(),
                assigned_node_name: String::new(),
                is_local: false,
                reason_code: "mesh_capability_disabled_cluster_wide".to_string(),
            }
        }
    }

    #[must_use]
    pub fn get_default_components(has_gpu: bool) -> Vec<NodeComponent> {
        vec![
            NodeComponent {
                id: "voice_studio".to_string(),
                name_key: "comp_voice_studio".to_string(),
                category: "ai_audio".to_string(),
                enabled: has_gpu,
                cpu_percent: if has_gpu { 6.5 } else { 28.0 },
                ram_mb: 850.0,
                gpu_percent: if has_gpu { 18.0 } else { 0.0 },
                vram_mb: if has_gpu { 1200.0 } else { 0.0 },
                delegable: true,
                delegated_to: None,
            },
            NodeComponent {
                id: "ollama_inference".to_string(),
                name_key: "comp_ollama_inference".to_string(),
                category: "ai_llm".to_string(),
                enabled: true,
                cpu_percent: if has_gpu { 4.0 } else { 35.0 },
                ram_mb: 2400.0,
                gpu_percent: if has_gpu { 32.0 } else { 0.0 },
                vram_mb: if has_gpu { 4500.0 } else { 0.0 },
                delegable: true,
                delegated_to: None,
            },
            NodeComponent {
                id: "vision_analyzer".to_string(),
                name_key: "comp_vision_analyzer".to_string(),
                category: "ai_vision".to_string(),
                enabled: has_gpu,
                cpu_percent: 5.0,
                ram_mb: 420.0,
                gpu_percent: if has_gpu { 12.0 } else { 0.0 },
                vram_mb: if has_gpu { 650.0 } else { 0.0 },
                delegable: true,
                delegated_to: None,
            },
            NodeComponent {
                id: "spatial_indexer".to_string(),
                name_key: "comp_spatial_indexer".to_string(),
                category: "indexing".to_string(),
                enabled: true,
                cpu_percent: 3.2,
                ram_mb: 680.0,
                gpu_percent: 0.0,
                vram_mb: 0.0,
                delegable: true,
                delegated_to: None,
            },
            NodeComponent {
                id: "satellite_broker".to_string(),
                name_key: "comp_satellite_broker".to_string(),
                category: "networking".to_string(),
                enabled: true,
                cpu_percent: 1.5,
                ram_mb: 180.0,
                gpu_percent: 0.0,
                vram_mb: 0.0,
                delegable: false,
                delegated_to: None,
            },
            NodeComponent {
                id: "mesh_router".to_string(),
                name_key: "comp_mesh_router".to_string(),
                category: "networking".to_string(),
                enabled: true,
                cpu_percent: 1.8,
                ram_mb: 220.0,
                gpu_percent: 0.0,
                vram_mb: 0.0,
                delegable: false,
                delegated_to: None,
            },
            NodeComponent {
                id: "system_kernel".to_string(),
                name_key: "comp_system_kernel".to_string(),
                category: "system".to_string(),
                enabled: true,
                cpu_percent: 2.1,
                ram_mb: 310.0,
                gpu_percent: 0.0,
                vram_mb: 0.0,
                delegable: false,
                delegated_to: None,
            },
        ]
    }
}
