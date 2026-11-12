use crate::errors::poisoned;
use pyo3::prelude::*;
use std::sync::{Arc, RwLock};

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAdminOsMemory {
    inner: Arc<RwLock<nuxiva_admin_os::MemoryManager>>,
}

#[pymethods]
impl RustAdminOsMemory {
    #[new]
    #[pyo3(signature = (warning_percent = 85.0, critical_percent = 92.0, critical_min_available_bytes = 268_435_456, warning_consecutive_threshold = 3))]
    fn new(
        warning_percent: f64,
        critical_percent: f64,
        critical_min_available_bytes: u64,
        warning_consecutive_threshold: u32,
    ) -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_admin_os::MemoryManager::new(
                warning_percent,
                critical_percent,
                critical_min_available_bytes,
                warning_consecutive_threshold,
            ))),
        }
    }

    fn evaluate(&self, total_bytes: u64, available_bytes: u64) -> PyResult<(String, bool, f64)> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let sample = guard.evaluate(total_bytes, available_bytes);
        let state_str = match sample.state {
            nuxiva_admin_os::MemoryState::Normal => "normal",
            nuxiva_admin_os::MemoryState::Warning => "warning",
            nuxiva_admin_os::MemoryState::Critical => "critical",
        };
        Ok((state_str.to_string(), sample.throttled, sample.percent))
    }

    fn is_throttled(&self) -> PyResult<bool> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.is_throttled())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAdminOsNotification {
    inner: Arc<RwLock<nuxiva_admin_os::NotificationManager>>,
}

#[pymethods]
impl RustAdminOsNotification {
    #[new]
    #[pyo3(signature = (max_items = 128, cooldown_secs = 30))]
    fn new(max_items: usize, cooldown_secs: u64) -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_admin_os::NotificationManager::new(
                max_items,
                cooldown_secs,
            ))),
        }
    }

    #[pyo3(signature = (level, title, message, timestamp_secs, force = false))]
    fn notify(
        &self,
        level: &str,
        title: &str,
        message: &str,
        timestamp_secs: u64,
        force: bool,
    ) -> PyResult<Option<u64>> {
        let lvl = match level.to_uppercase().as_str() {
            "CRITICAL" => nuxiva_admin_os::NotificationLevel::Critical,
            "WARNING" => nuxiva_admin_os::NotificationLevel::Warning,
            _ => nuxiva_admin_os::NotificationLevel::Info,
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let item = guard.notify(lvl, title, message, timestamp_secs, force);
        Ok(item.map(|i| i.id))
    }

    fn count(&self) -> PyResult<usize> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.count())
    }

    fn clear(&self) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.clear();
        Ok(())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAdminOsAiEngine {
    inner: Arc<RwLock<nuxiva_admin_os::AiEngineManager>>,
}

#[pymethods]
impl RustAdminOsAiEngine {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(nuxiva_admin_os::AiEngineManager::new(
                nuxiva_admin_os::InferenceConfig::default(),
            ))),
        }
    }

    #[staticmethod]
    fn recommend_threads(physical_cores: u16) -> u16 {
        nuxiva_admin_os::AiEngineManager::recommend_threads(physical_cores)
    }

    #[staticmethod]
    fn recommend_context_window(available_ram_gb: u32, is_gpu_accelerated: bool) -> u32 {
        nuxiva_admin_os::AiEngineManager::recommend_context_window(
            available_ram_gb,
            is_gpu_accelerated,
        )
    }

    fn loaded_count(&self) -> PyResult<usize> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.status(true).active_models_count)
    }

    fn catalog_count(&self) -> PyResult<usize> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.status(true).total_models_catalog)
    }

    #[staticmethod]
    fn calculate_tokens_per_second(
        generated_tokens: u32,
        eval_ms: u64,
        prompt_tokens: u32,
        prompt_eval_ms: u64,
    ) -> (f32, f32) {
        let telem = nuxiva_admin_os::InferenceTelemetry {
            prompt_tokens,
            prompt_eval_ms,
            generated_tokens,
            eval_ms,
            vram_bytes: 0,
        };
        (telem.tokens_per_second(), telem.prompt_tokens_per_second())
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustAdminOsFirewall {
    inner: Arc<RwLock<nuxiva_admin_os::FirewallEngine>>,
}

#[pymethods]
impl RustAdminOsFirewall {
    #[new]
    #[pyo3(signature = (mode = "protect"))]
    fn new(mode: &str) -> Self {
        let fw_mode = match mode {
            "off" => nuxiva_admin_os::FirewallMode::Off,
            "monitor" => nuxiva_admin_os::FirewallMode::Monitor,
            "lockdown" => nuxiva_admin_os::FirewallMode::Lockdown,
            _ => nuxiva_admin_os::FirewallMode::Protect,
        };
        Self {
            inner: Arc::new(RwLock::new(nuxiva_admin_os::FirewallEngine::new(fw_mode))),
        }
    }

    #[pyo3(signature = (address, duration_secs, reason, now))]
    fn block_address(
        &self,
        address: &str,
        duration_secs: Option<u64>,
        reason: &str,
        now: u64,
    ) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.block_address(address, duration_secs, reason, now);
        Ok(())
    }

    fn is_blocked(&self, address: &str, now: u64) -> PyResult<bool> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.is_blocked(address, now))
    }

    fn cleanup_expired_blocks(&self, now: u64) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard.cleanup_expired_blocks(now);
        Ok(())
    }

    fn evaluate(
        &self,
        direction: &str,
        protocol: &str,
        src_ip: &str,
        dst_port: Option<u16>,
        now: u64,
    ) -> PyResult<String> {
        let dir = match direction {
            "output" => nuxiva_admin_os::RuleDirection::Output,
            "forward" => nuxiva_admin_os::RuleDirection::Forward,
            _ => nuxiva_admin_os::RuleDirection::Input,
        };
        let proto = match protocol {
            "tcp" => nuxiva_admin_os::RuleProtocol::Tcp,
            "udp" => nuxiva_admin_os::RuleProtocol::Udp,
            "icmp" => nuxiva_admin_os::RuleProtocol::Icmp,
            _ => nuxiva_admin_os::RuleProtocol::Any,
        };
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let action = guard.evaluate(dir, proto, src_ip, dst_port, now);
        let action_str = match action {
            nuxiva_admin_os::RuleAction::Accept => "accept",
            nuxiva_admin_os::RuleAction::Drop => "drop",
            nuxiva_admin_os::RuleAction::Reject => "reject",
            nuxiva_admin_os::RuleAction::Limit => "limit",
        };
        Ok(action_str.to_string())
    }
}
