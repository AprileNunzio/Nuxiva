mod gate;
mod plan;

use nuxiva_agent_core::ceo::Decision;

use crate::catalog::Catalog;
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;
use crate::wire::{Constraints, Digest, Ident, Level, Plan, SCHEMA_VERSION, TaskEnvelope, decode};

pub use gate::GraphGate;
pub use plan::{check_budget, critical_path_ms, deterministic, level_budget, pick_intent};

pub trait Planner: Send + Sync {
    fn propose(&self, prompt: &PlanPrompt) -> SwarmResult<Vec<u8>>;
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct PlanPrompt {
    pub task: TaskEnvelope,
    pub offers: Vec<Offer>,
    pub attempt: usize,
    pub rejected: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Offer {
    pub worker_template: Ident,
    pub intents: Vec<Ident>,
    pub needs_graph: bool,
    pub tokens_max: u64,
    pub tool_calls_max: u64,
    pub time_ms: u64,
}

#[derive(Debug)]
pub struct Request<'a> {
    pub id: Ident,
    pub input: Ident,
    pub text: &'a str,
    pub context_ref: Option<Ident>,
    pub graph_ref: Option<Digest>,
    pub risk_max: u8,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Admission {
    Direct,
    Task(Box<TaskEnvelope>),
}

#[derive(Debug)]
pub struct Supervisor {
    catalog: Catalog,
    settings: Settings,
    gate: GraphGate,
}

impl Supervisor {
    pub fn new(catalog: Catalog, settings: Settings) -> SwarmResult<Self> {
        settings.validate()?;
        let gate = GraphGate::new(&settings);
        Ok(Self {
            catalog,
            settings,
            gate,
        })
    }

    #[must_use]
    pub const fn gate(&self) -> &GraphGate {
        &self.gate
    }

    #[must_use]
    pub const fn catalog(&self) -> &Catalog {
        &self.catalog
    }

    pub fn admit(&self, decision: &Decision, request: &Request<'_>) -> SwarmResult<Admission> {
        if decision.conversational || decision.primary.is_empty() {
            return Ok(Admission::Direct);
        }
        let template = self
            .catalog
            .template(&Ident::new(&decision.primary)?)
            .ok_or(SwarmError::UnknownTemplate)?;
        let intent = pick_intent(template, request.text).ok_or(SwarmError::UnknownIntent)?;
        let level = Level::from(decision.level);
        let budget = level_budget(&self.settings, level);
        let task = TaskEnvelope {
            schema_version: SCHEMA_VERSION,
            id: request.id.clone(),
            intent,
            input: request.input.clone(),
            constraints: Constraints {
                risk_max: request.risk_max,
                deadline_ms: budget.time_ms,
                tokens_max: budget.tokens,
                tool_calls_max: budget.tool_calls,
                level,
            },
            parent: None,
            context_ref: request.context_ref.clone(),
            graph_ref: request.graph_ref.clone(),
            depth: 0,
        };
        self.catalog.check_task(&task, &self.settings)?;
        Ok(Admission::Task(Box::new(task)))
    }

    fn offers(&self) -> Vec<Offer> {
        self.catalog
            .templates()
            .map(|t| Offer {
                worker_template: t.agent.clone(),
                intents: t.intents.clone(),
                needs_graph: t.needs_graph,
                tokens_max: t.tokens_max,
                tool_calls_max: t.tool_calls_max,
                time_ms: t.time_ms,
            })
            .collect()
    }

    fn accept(&self, raw: &[u8], task: &TaskEnvelope, now_ms: u64) -> SwarmResult<Plan> {
        let plan: Plan = decode(raw, &self.settings)?;
        self.catalog.check_plan(&plan, &self.settings)?;
        check_budget(&plan, task)?;
        self.gate.check_plan(&plan, task, now_ms)?;
        Ok(plan)
    }

    fn propose(
        &self,
        planner: &dyn Planner,
        task: &TaskEnvelope,
        now_ms: u64,
    ) -> SwarmResult<Plan> {
        let mut rejected: Option<SwarmError> = None;
        for attempt in 0..=self.settings.repair_attempts {
            let prompt = PlanPrompt {
                task: task.clone(),
                offers: self.offers(),
                attempt,
                rejected: rejected.map(|e| e.code().to_owned()),
            };
            let raw = planner
                .propose(&prompt)
                .map_err(|_| SwarmError::PlannerFailed)?;
            match self.accept(&raw, task, now_ms) {
                Ok(plan) => return Ok(plan),
                Err(error) => rejected = Some(error),
            }
        }
        Err(rejected.unwrap_or(SwarmError::PlannerFailed))
    }

    pub fn plan(
        &self,
        task: &TaskEnvelope,
        decision: &Decision,
        text: &str,
        planner: Option<&dyn Planner>,
        now_ms: u64,
    ) -> SwarmResult<Plan> {
        let plan = match (task.constraints.level, planner) {
            (Level::Lampo, _) | (Level::Standard, None) => {
                deterministic(&self.catalog, &self.settings, task, decision, text)?
            }
            (_, Some(planner)) => self.propose(planner, task, now_ms)?,
            (Level::Progetto, None) => return Err(SwarmError::NoPlanner),
        };
        self.gate.check_plan(&plan, task, now_ms)?;
        Ok(plan)
    }
}
