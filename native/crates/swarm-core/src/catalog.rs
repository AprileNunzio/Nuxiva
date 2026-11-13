use std::collections::BTreeMap;

use nuxiva_agent_core::Manifest;
use nuxiva_agent_core::text::normalize;

use crate::error::{SwarmError, SwarmResult};
use crate::limits::Ceilings;
use crate::settings::Settings;
use crate::wire::ident::valid_token;
use crate::wire::{Ident, Plan, TaskEnvelope, Validate};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerTemplate {
    pub agent: Ident,
    pub kind: String,
    pub concurrency_max: u64,
    pub tokens_max: u64,
    pub tool_calls_max: u64,
    pub time_ms: u64,
    pub tools_scope: Vec<String>,
    pub needs_graph: bool,
    pub intents: Vec<Ident>,
}

#[must_use]
pub fn intent_slug(text: &str) -> Option<Ident> {
    let slug = normalize(text).replace(' ', "_");
    if valid_token(&slug, Ceilings::IDENT) {
        Ident::new(&slug).ok()
    } else {
        None
    }
}

fn or_default(value: u64, default: u64) -> u64 {
    if value == 0 { default } else { value }
}

fn template(manifest: &Manifest, settings: &Settings) -> SwarmResult<WorkerTemplate> {
    let agent = Ident::new(&manifest.id)?;
    let block = manifest.worker.clone().unwrap_or_default();
    let kind = if block.kind.is_empty() {
        settings.default_worker_kind.clone()
    } else {
        block.kind
    };
    let tokens_max = or_default(block.tokens_max, settings.default_tokens);
    let tool_calls_max = or_default(block.tool_calls_max, settings.default_tool_calls);
    let time_ms = or_default(block.time_ms, settings.default_time_ms);
    let concurrency_max = or_default(block.concurrency_max, settings.default_concurrency);
    let within = tokens_max <= settings.max_tokens
        && tool_calls_max <= settings.max_tool_calls
        && time_ms <= settings.max_time_ms
        && usize::try_from(concurrency_max).is_ok_and(|c| c <= settings.max_workers);
    if !within {
        return Err(SwarmError::Budget);
    }
    let mut intents: Vec<Ident> = Vec::new();
    for capability in &manifest.capabilities {
        if let Some(intent) = intent_slug(capability) {
            if !intents.contains(&intent) && intents.len() < Ceilings::INTENTS_PER_AGENT {
                intents.push(intent);
            }
        }
    }
    Ok(WorkerTemplate {
        agent,
        kind,
        concurrency_max,
        tokens_max,
        tool_calls_max,
        time_ms,
        tools_scope: block.tools_scope,
        needs_graph: block.needs_graph,
        intents,
    })
}

#[derive(Debug, Clone, Default)]
pub struct Catalog {
    templates: BTreeMap<Ident, WorkerTemplate>,
    intents: BTreeMap<Ident, Vec<Ident>>,
}

impl Catalog {
    pub fn build(manifests: &[Manifest], settings: &Settings) -> SwarmResult<Self> {
        settings.validate()?;
        let mut catalog = Self::default();
        for manifest in manifests {
            let built = template(manifest, settings)?;
            if catalog.templates.contains_key(&built.agent) {
                return Err(SwarmError::Invalid);
            }
            for intent in &built.intents {
                catalog
                    .intents
                    .entry(intent.clone())
                    .or_default()
                    .push(built.agent.clone());
            }
            catalog.templates.insert(built.agent.clone(), built);
        }
        Ok(catalog)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.templates.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.templates.is_empty()
    }

    pub fn templates(&self) -> impl Iterator<Item = &WorkerTemplate> {
        self.templates.values()
    }

    #[must_use]
    pub fn template(&self, agent: &Ident) -> Option<&WorkerTemplate> {
        self.templates.get(agent)
    }

    #[must_use]
    pub fn agents_for(&self, intent: &Ident) -> &[Ident] {
        self.intents.get(intent).map_or(&[], Vec::as_slice)
    }

    #[must_use]
    pub fn knows_intent(&self, intent: &Ident) -> bool {
        self.intents.contains_key(intent)
    }

    pub fn check_task(&self, task: &TaskEnvelope, settings: &Settings) -> SwarmResult<()> {
        task.validate(settings)?;
        if self.knows_intent(&task.intent) {
            Ok(())
        } else {
            Err(SwarmError::UnknownIntent)
        }
    }

    pub fn check_plan(&self, plan: &Plan, settings: &Settings) -> SwarmResult<()> {
        plan.validate(settings)?;
        for step in &plan.steps {
            let template = self
                .templates
                .get(&step.worker_template)
                .ok_or(SwarmError::UnknownTemplate)?;
            if !self.knows_intent(&step.intent) {
                return Err(SwarmError::UnknownIntent);
            }
            if !template.intents.contains(&step.intent) {
                return Err(SwarmError::IntentMismatch);
            }
            let budget = &step.budget;
            if budget.tokens > template.tokens_max
                || budget.tool_calls > template.tool_calls_max
                || budget.time_ms > template.time_ms
            {
                return Err(SwarmError::Budget);
            }
            if template.needs_graph && !step.needs_graph {
                return Err(SwarmError::Invalid);
            }
        }
        Ok(())
    }
}
