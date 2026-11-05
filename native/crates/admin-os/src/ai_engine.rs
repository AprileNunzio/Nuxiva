use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelQuantization {
    Q4KM,
    Q5KM,
    Q80,
    Fp16,
    Bf16,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelKind {
    Llm,
    Vision,
    Audio,
    Embedding,
    Code,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModelProfile {
    pub id: String,
    pub name: String,
    pub size_bytes: u64,
    pub parameter_count: u64,
    pub context_limit: u32,
    pub quantization: ModelQuantization,
    pub kind: ModelKind,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InferenceConfig {
    pub num_ctx: u32,
    pub num_predict: u32,
    pub num_parallel: u16,
    pub num_thread: u16,
    pub flash_attention: bool,
    pub keep_alive_seconds: i64,
    pub temperature: f32,
}

impl Default for InferenceConfig {
    fn default() -> Self {
        Self {
            num_ctx: 4096,
            num_predict: 2048,
            num_parallel: 2,
            num_thread: 4,
            flash_attention: true,
            keep_alive_seconds: 86400,
            temperature: 0.7,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct InferenceTelemetry {
    pub prompt_tokens: u32,
    pub prompt_eval_ms: u64,
    pub generated_tokens: u32,
    pub eval_ms: u64,
    pub vram_bytes: u64,
}

impl InferenceTelemetry {
    #[must_use]
    #[allow(clippy::cast_precision_loss)]
    pub fn tokens_per_second(&self) -> f32 {
        if self.eval_ms == 0 {
            0.0
        } else {
            (self.generated_tokens as f32 * 1000.0) / (self.eval_ms as f32)
        }
    }

    #[must_use]
    #[allow(clippy::cast_precision_loss)]
    pub fn prompt_tokens_per_second(&self) -> f32 {
        if self.prompt_eval_ms == 0 {
            0.0
        } else {
            (self.prompt_tokens as f32 * 1000.0) / (self.prompt_eval_ms as f32)
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AiEngineStatus {
    pub online: bool,
    pub active_models_count: usize,
    pub total_models_catalog: usize,
    pub total_vram_used_bytes: u64,
    pub flash_attention_active: bool,
}

#[derive(Debug, Clone, Default)]
pub struct AiEngineManager {
    catalog: Vec<ModelProfile>,
    loaded_models: Vec<String>,
    config: InferenceConfig,
    telemetry: InferenceTelemetry,
}

impl AiEngineManager {
    #[must_use]
    pub fn new(config: InferenceConfig) -> Self {
        Self {
            catalog: Vec::new(),
            loaded_models: Vec::new(),
            config,
            telemetry: InferenceTelemetry::default(),
        }
    }

    pub fn register_model(&mut self, profile: ModelProfile) {
        if let Some(pos) = self.catalog.iter().position(|m| m.id == profile.id) {
            if let Some(existing) = self.catalog.get_mut(pos) {
                *existing = profile;
            }
        } else {
            self.catalog.push(profile);
        }
    }

    pub fn unregister_model(&mut self, model_id: &str) -> bool {
        let initial_len = self.catalog.len();
        self.catalog.retain(|m| m.id != model_id);
        self.loaded_models.retain(|id| id != model_id);
        self.catalog.len() < initial_len
    }

    pub fn load_model(&mut self, model_id: &str, max_loaded: usize) -> Result<(), &'static str> {
        let exists = self.catalog.iter().any(|m| m.id == model_id);
        if !exists {
            return Err("model_not_found");
        }
        if self.loaded_models.iter().any(|id| id == model_id) {
            return Ok(());
        }
        if self.loaded_models.len() >= max_loaded && max_loaded > 0 {
            self.loaded_models.remove(0);
        }
        self.loaded_models.push(model_id.to_string());
        Ok(())
    }

    pub fn unload_model(&mut self, model_id: &str) -> bool {
        let initial_len = self.loaded_models.len();
        self.loaded_models.retain(|id| id != model_id);
        self.loaded_models.len() < initial_len
    }

    pub fn update_config(&mut self, new_config: InferenceConfig) {
        self.config = new_config;
    }

    pub fn record_telemetry(&mut self, telemetry: InferenceTelemetry) {
        self.telemetry = telemetry;
    }

    #[must_use]
    pub fn get_config(&self) -> &InferenceConfig {
        &self.config
    }

    #[must_use]
    pub fn get_telemetry(&self) -> &InferenceTelemetry {
        &self.telemetry
    }

    #[must_use]
    pub fn get_catalog(&self) -> &[ModelProfile] {
        &self.catalog
    }

    #[must_use]
    pub fn get_loaded_models(&self) -> &[String] {
        &self.loaded_models
    }

    #[must_use]
    pub fn recommend_threads(physical_cores: u16) -> u16 {
        if physical_cores <= 2 {
            1
        } else if physical_cores <= 4 {
            2
        } else if physical_cores <= 8 {
            4
        } else {
            physical_cores.saturating_sub(2).max(4)
        }
    }

    #[must_use]
    pub fn recommend_context_window(available_ram_gb: u32, is_gpu_accelerated: bool) -> u32 {
        if is_gpu_accelerated {
            if available_ram_gb >= 32 {
                32768
            } else if available_ram_gb >= 16 {
                16384
            } else if available_ram_gb >= 8 {
                8192
            } else {
                4096
            }
        } else if available_ram_gb >= 16 {
            8192
        } else if available_ram_gb >= 8 {
            4096
        } else {
            2048
        }
    }

    #[must_use]
    pub fn status(&self, online: bool) -> AiEngineStatus {
        AiEngineStatus {
            online,
            active_models_count: self.loaded_models.len(),
            total_models_catalog: self.catalog.len(),
            total_vram_used_bytes: self.telemetry.vram_bytes,
            flash_attention_active: self.config.flash_attention,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_telemetry_rates() {
        let t = InferenceTelemetry {
            prompt_tokens: 50,
            prompt_eval_ms: 1000,
            generated_tokens: 100,
            eval_ms: 2000,
            vram_bytes: 4_000_000_000,
        };
        assert!((t.tokens_per_second() - 50.0).abs() < f32::EPSILON);
        assert!((t.prompt_tokens_per_second() - 50.0).abs() < f32::EPSILON);

        let zero = InferenceTelemetry::default();
        assert!(zero.tokens_per_second().abs() < f32::EPSILON);
        assert!(zero.prompt_tokens_per_second().abs() < f32::EPSILON);
    }

    #[test]
    fn test_model_catalog_and_loading() {
        let mut mgr = AiEngineManager::new(InferenceConfig::default());
        let m1 = ModelProfile {
            id: "llama3:8b".to_string(),
            name: "Llama 3 8B Instruct".to_string(),
            size_bytes: 4_700_000_000,
            parameter_count: 8_000_000_000,
            context_limit: 8192,
            quantization: ModelQuantization::Q4KM,
            kind: ModelKind::Llm,
        };
        let m2 = ModelProfile {
            id: "nomic-embed:latest".to_string(),
            name: "Nomic Embed Text".to_string(),
            size_bytes: 270_000_000,
            parameter_count: 137_000_000,
            context_limit: 2048,
            quantization: ModelQuantization::Fp16,
            kind: ModelKind::Embedding,
        };

        mgr.register_model(m1);
        mgr.register_model(m2);
        assert_eq!(mgr.get_catalog().len(), 2);

        assert!(mgr.load_model("unknown", 2).is_err());
        assert!(mgr.load_model("llama3:8b", 2).is_ok());
        assert_eq!(mgr.get_loaded_models().len(), 1);

        assert!(mgr.load_model("llama3:8b", 2).is_ok());
        assert_eq!(mgr.get_loaded_models().len(), 1);

        assert!(mgr.load_model("nomic-embed:latest", 1).is_ok());
        assert_eq!(mgr.get_loaded_models().len(), 1);
        assert_eq!(
            mgr.get_loaded_models().first().map(String::as_str),
            Some("nomic-embed:latest")
        );

        assert!(mgr.unload_model("nomic-embed:latest"));
        assert!(!mgr.unload_model("nomic-embed:latest"));
    }

    #[test]
    fn test_recommendations() {
        assert_eq!(AiEngineManager::recommend_threads(2), 1);
        assert_eq!(AiEngineManager::recommend_threads(4), 2);
        assert_eq!(AiEngineManager::recommend_threads(8), 4);
        assert_eq!(AiEngineManager::recommend_threads(16), 14);

        assert_eq!(AiEngineManager::recommend_context_window(4, false), 2048);
        assert_eq!(AiEngineManager::recommend_context_window(8, false), 4096);
        assert_eq!(AiEngineManager::recommend_context_window(16, false), 8192);
        assert_eq!(AiEngineManager::recommend_context_window(8, true), 8192);
        assert_eq!(AiEngineManager::recommend_context_window(16, true), 16384);
        assert_eq!(AiEngineManager::recommend_context_window(32, true), 32768);
    }

    #[test]
    fn test_status() {
        let mut mgr = AiEngineManager::new(InferenceConfig::default());
        let st = mgr.status(true);
        assert!(st.online);
        assert!(st.flash_attention_active);
        assert_eq!(st.active_models_count, 0);

        let mut conf = mgr.get_config().clone();
        conf.flash_attention = false;
        mgr.update_config(conf);
        let st2 = mgr.status(false);
        assert!(!st2.online);
        assert!(!st2.flash_attention_active);
    }
}
