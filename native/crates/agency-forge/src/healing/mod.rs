use serde::{Deserialize, Serialize};

use crate::error::ForgeError;

pub const MAX_REPAIR_ATTEMPTS: u8 = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FailureCause {
    MissingCapability,
    SchemaDrift,
    EndpointRelocated,
    AuthExpired,
    TimeoutOrTransient,
    SandboxGuardViolation,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RepairStrategy {
    SynthesizeNewTool,
    NormalizePayloadSchema,
    RerouteCanonicalEndpoint,
    RefreshCredentialContext,
    RetryWithDeterministicFallback,
    RewritePureFunction,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FailureContext {
    pub task_id: String,
    pub intent: String,
    pub tool_or_agent: String,
    pub error_message: String,
    pub attempt: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SelfHealingPlan {
    pub task_id: String,
    pub cause: FailureCause,
    pub strategy: RepairStrategy,
    pub can_auto_repair: bool,
    pub target_tool_name: String,
    pub repair_directive_key: String,
    pub remaining_attempts: u8,
}

fn sanitize_identifier(raw: &str) -> String {
    let cleaned: String = raw
        .trim()
        .to_lowercase()
        .chars()
        .map(|c| {
            if c.is_ascii_lowercase() || c.is_ascii_digit() {
                c
            } else {
                '_'
            }
        })
        .collect();
    let collapsed = cleaned
        .split('_')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("_");
    if collapsed.len() < 3 {
        format!("auto_skill_{collapsed}")
    } else {
        collapsed.chars().take(36).collect()
    }
}

pub fn formulate_healing_plan(ctx: &FailureContext) -> Result<SelfHealingPlan, ForgeError> {
    if ctx.task_id.trim().is_empty() || ctx.intent.trim().is_empty() {
        return Err(ForgeError::InvalidName("empty task or intent".to_owned()));
    }
    let lower = ctx.error_message.to_lowercase();

    let (cause, strategy, directive_key) =
        if lower.contains("no agent") || lower.contains("missing") || lower.contains("not found") {
            if lower.contains("404") || lower.contains("endpoint") {
                (
                    FailureCause::EndpointRelocated,
                    RepairStrategy::RerouteCanonicalEndpoint,
                    "i18n.healing.reroute_endpoint",
                )
            } else {
                (
                    FailureCause::MissingCapability,
                    RepairStrategy::SynthesizeNewTool,
                    "i18n.healing.synthesize_missing_tool",
                )
            }
        } else if lower.contains("schema")
            || lower.contains("keyerror")
            || lower.contains("field")
            || lower.contains("json")
        {
            (
                FailureCause::SchemaDrift,
                RepairStrategy::NormalizePayloadSchema,
                "i18n.healing.normalize_schema",
            )
        } else if lower.contains("401") || lower.contains("403") || lower.contains("auth") {
            (
                FailureCause::AuthExpired,
                RepairStrategy::RefreshCredentialContext,
                "i18n.healing.refresh_credentials",
            )
        } else if lower.contains("forbidden") || lower.contains("guard") || lower.contains("import")
        {
            (
                FailureCause::SandboxGuardViolation,
                RepairStrategy::RewritePureFunction,
                "i18n.healing.rewrite_pure_function",
            )
        } else {
            (
                FailureCause::TimeoutOrTransient,
                RepairStrategy::RetryWithDeterministicFallback,
                "i18n.healing.deterministic_fallback",
            )
        };

    let can_auto_repair = ctx.attempt < MAX_REPAIR_ATTEMPTS;
    let remaining_attempts = MAX_REPAIR_ATTEMPTS.saturating_sub(ctx.attempt);
    let target_tool_name = sanitize_identifier(&ctx.intent);

    Ok(SelfHealingPlan {
        task_id: ctx.task_id.trim().to_owned(),
        cause,
        strategy,
        can_auto_repair,
        target_tool_name,
        repair_directive_key: directive_key.to_owned(),
        remaining_attempts,
    })
}
