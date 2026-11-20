use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActionCommandSpec {
    pub command: String,
    pub working_dir: String,
    pub modified_files: Vec<String>,
    pub payload_bytes: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ActionInvariant {
    FilesystemBoundary {
        allowed_root: String,
    },
    ForbiddenPatterns {
        blacklisted_tokens: Vec<String>,
    },
    ResourceQuota {
        max_payload_bytes: usize,
        max_files: usize,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PreflightVerdict {
    Allowed,
    Denied { invariant: String, reason: String },
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PreflightSimulator {
    invariants: Vec<ActionInvariant>,
}

impl PreflightSimulator {
    #[must_use]
    pub const fn new(invariants: Vec<ActionInvariant>) -> Self {
        Self { invariants }
    }

    pub fn add_invariant(&mut self, invariant: ActionInvariant) {
        self.invariants.push(invariant);
    }

    #[must_use]
    pub fn evaluate(&self, spec: &ActionCommandSpec) -> PreflightVerdict {
        for invariant in &self.invariants {
            match invariant {
                ActionInvariant::FilesystemBoundary { allowed_root } => {
                    if !spec.working_dir.starts_with(allowed_root) {
                        return PreflightVerdict::Denied {
                            invariant: "FilesystemBoundary".to_string(),
                            reason: format!(
                                "working directory {} outside allowed root {allowed_root}",
                                spec.working_dir
                            ),
                        };
                    }
                    for file in &spec.modified_files {
                        if !file.starts_with(allowed_root) || file.contains("/../") {
                            return PreflightVerdict::Denied {
                                invariant: "FilesystemBoundary".to_string(),
                                reason: format!(
                                    "target path {file} escapes allowed root {allowed_root}"
                                ),
                            };
                        }
                    }
                }
                ActionInvariant::ForbiddenPatterns { blacklisted_tokens } => {
                    for token in blacklisted_tokens {
                        if spec.command.contains(token) {
                            return PreflightVerdict::Denied {
                                invariant: "ForbiddenPatterns".to_string(),
                                reason: format!("command contains blacklisted token: {token}"),
                            };
                        }
                    }
                }
                ActionInvariant::ResourceQuota {
                    max_payload_bytes,
                    max_files,
                } => {
                    if spec.payload_bytes > *max_payload_bytes {
                        return PreflightVerdict::Denied {
                            invariant: "ResourceQuota".to_string(),
                            reason: format!(
                                "payload bytes {} exceeds limit {max_payload_bytes}",
                                spec.payload_bytes
                            ),
                        };
                    }
                    if spec.modified_files.len() > *max_files {
                        return PreflightVerdict::Denied {
                            invariant: "ResourceQuota".to_string(),
                            reason: format!(
                                "file count {} exceeds quota {max_files}",
                                spec.modified_files.len()
                            ),
                        };
                    }
                }
            }
        }
        PreflightVerdict::Allowed
    }
}
