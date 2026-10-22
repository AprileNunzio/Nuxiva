use crate::errors::poisoned;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::{Arc, RwLock};

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustResourceGovernor {
    inner: Arc<RwLock<nuxiva_spatial_core::ResourceGovernor>>,
}

#[pymethods]
impl RustResourceGovernor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::ResourceGovernor::new())),
        }
    }

    #[staticmethod]
    fn normalize_ollama_url(raw_host: &str) -> String {
        nuxiva_spatial_core::ResourceGovernor::normalize_ollama_url(raw_host)
    }

    fn register_remote_server(&self, id: &str, raw_host: &str) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_remote_server(id, raw_host);
        Ok(())
    }

    fn set_target_allocation(
        &self,
        target_id: &str,
        provider_str: &str,
        model_name: &str,
        node_url: Option<String>,
    ) -> PyResult<()> {
        let provider = match provider_str {
            "ollama_local" => nuxiva_spatial_core::ComputeProvider::OllamaLocal,
            "ollama_remote" => nuxiva_spatial_core::ComputeProvider::OllamaRemote,
            _ => nuxiva_spatial_core::ComputeProvider::ApiKey,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.set_target_allocation(nuxiva_spatial_core::TargetAllocation {
            target_id: target_id.to_string(),
            provider,
            model_name: model_name.to_string(),
            node_url,
        });
        Ok(())
    }

    #[allow(clippy::needless_pass_by_value)]
    fn apply_global_default_to_all(
        &self,
        provider_str: &str,
        model_name: &str,
        node_url: Option<String>,
    ) -> PyResult<()> {
        let provider = match provider_str {
            "ollama_local" => nuxiva_spatial_core::ComputeProvider::OllamaLocal,
            "ollama_remote" => nuxiva_spatial_core::ComputeProvider::OllamaRemote,
            _ => nuxiva_spatial_core::ComputeProvider::ApiKey,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.apply_global_default_to_all(provider, model_name, node_url.as_deref());
        Ok(())
    }

    fn evaluate_resource_plan_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let plan = guard.evaluate_resource_plan();
        serde_json::to_string(&plan).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[derive(Debug, Default)]
#[pyclass(module = "nuxiva_native")]
pub struct RustMeshTaskGovernor {
    inner: Arc<RwLock<nuxiva_spatial_core::MeshTaskGovernor>>,
}

#[pymethods]
impl RustMeshTaskGovernor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::MeshTaskGovernor::new())),
        }
    }

    fn register_or_update_node_json(&self, profile_json: &str) -> PyResult<()> {
        let profile: nuxiva_spatial_core::NodeProfile = serde_json::from_str(profile_json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_or_update_node(profile);
        Ok(())
    }

    fn get_node_json(&self, node_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        if let Some(profile) = guard.get_node(node_id) {
            let json = serde_json::to_string(profile)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            Ok(Some(json))
        } else {
            Ok(None)
        }
    }

    fn toggle_component(&self, node_id: &str, component_id: &str, enabled: bool) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.toggle_component(node_id, component_id, enabled))
    }

    fn evaluate_node_json(&self, node_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        if let Some(eval) = guard.evaluate_node(node_id) {
            let json =
                serde_json::to_string(&eval).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            Ok(Some(json))
        } else {
            Ok(None)
        }
    }

    fn resolve_capability_dispatch_json(
        &self,
        requesting_node_id: &str,
        capability: &str,
    ) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let res = guard.resolve_capability_dispatch(requesting_node_id, capability);
        serde_json::to_string(&res).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[staticmethod]
    fn get_default_components_json(has_gpu: bool) -> PyResult<String> {
        let comps = nuxiva_spatial_core::MeshTaskGovernor::get_default_components(has_gpu);
        serde_json::to_string(&comps).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[derive(Debug, Default)]
#[pyclass(module = "nuxiva_native")]
pub struct RustNetworkGovernor {
    inner: Arc<RwLock<nuxiva_spatial_core::NetworkGovernor>>,
}

#[pymethods]
impl RustNetworkGovernor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_spatial_core::NetworkGovernor::new())),
        }
    }

    fn register_or_update_profile_json(&self, profile_json: &str) -> PyResult<()> {
        let prof: nuxiva_spatial_core::NodeNetworkProfile = serde_json::from_str(profile_json)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.register_or_update_profile(prof);
        Ok(())
    }

    fn get_profile_json(&self, node_id: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        if let Some(prof) = guard.get_profile(node_id) {
            let json =
                serde_json::to_string(prof).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            Ok(Some(json))
        } else {
            Ok(None)
        }
    }

    fn set_policy(&self, node_id: &str, policy_str: &str) -> PyResult<bool> {
        let policy = match policy_str {
            "ethernet_only" => nuxiva_spatial_core::ConnectionRoutingPolicy::EthernetOnly,
            "wifi_only" => nuxiva_spatial_core::ConnectionRoutingPolicy::WifiOnly,
            "dual_aggregation" => nuxiva_spatial_core::ConnectionRoutingPolicy::DualAggregation,
            _ => nuxiva_spatial_core::ConnectionRoutingPolicy::Fallback,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.set_policy(node_id, policy))
    }

    fn toggle_interface(&self, node_id: &str, interface_name: &str, is_up: bool) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.toggle_interface(node_id, interface_name, is_up))
    }

    fn toggle_vpn(&self, node_id: &str, enabled: bool) -> PyResult<bool> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        Ok(guard.toggle_vpn(node_id, enabled))
    }

    #[allow(clippy::too_many_arguments, clippy::needless_pass_by_value)]
    fn update_interface_ip_config(
        &self,
        node_id: &str,
        interface_name: &str,
        mode_str: &str,
        ipv4: Option<String>,
        netmask: Option<String>,
        gateway: Option<String>,
        dns_primary: Option<String>,
        dns_secondary: Option<String>,
    ) -> PyResult<()> {
        let mode = match mode_str {
            "static" => nuxiva_spatial_core::IpAssignmentMode::Static,
            _ => nuxiva_spatial_core::IpAssignmentMode::Dhcp,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard
            .update_interface_ip_config(
                node_id,
                interface_name,
                mode,
                ipv4,
                netmask,
                gateway,
                dns_primary,
                dns_secondary,
            )
            .map_err(PyRuntimeError::new_err)
    }

    fn determine_active_route_json(&self, node_id: &str) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let route = guard.determine_active_route(node_id);
        serde_json::to_string(&route).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    #[staticmethod]
    fn get_default_profile_json(node_id: &str, node_ip: Option<&str>) -> PyResult<String> {
        let prof = nuxiva_spatial_core::NetworkGovernor::get_default_profile(node_id, node_ip);
        serde_json::to_string(&prof).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}
