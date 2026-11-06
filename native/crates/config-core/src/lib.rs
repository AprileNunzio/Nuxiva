#![forbid(unsafe_code)]

mod envstore;
mod keys;
mod ollama;
mod plan;

pub use envstore::{ConfigError, parse_env, rewrite_env};
pub use keys::{is_secret, valid_key};
pub use ollama::{DEFAULT_OLLAMA_PORT, normalize_ollama, ollama_remote, ollama_url};
pub use plan::{STEP_TRIGGERS, apply_plan, reload_units};

#[cfg(test)]
mod tests;
