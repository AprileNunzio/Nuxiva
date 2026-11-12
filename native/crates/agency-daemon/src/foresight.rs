use std::collections::BTreeMap;
use std::path::PathBuf;

use agency_domain::ProjectId;
use agency_foresight::{Ensemble, EventSpec, Leaning, ScenarioSpec, World, WorldState};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::error::AgencyError;
use crate::files;
use crate::seal::Sealer;

const MAX_SIMULATIONS: usize = 64;
const STEP_WORK: usize = 200_000;
const INDEX: &str = "index";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Summary {
    pub id: String,
    pub title: String,
    pub question: String,
    pub round: u16,
    pub rounds: u16,
    pub agents: u32,
    pub events: u32,
    pub leaning: Leaning,
    pub mean: f64,
    pub polarization: f64,
    pub created_ms: u64,
    pub updated_ms: u64,
    pub ensemble: Option<Ensemble>,
}

#[derive(Debug)]
pub struct Foresight {
    dir: PathBuf,
    sealer: Sealer,
    index: BTreeMap<String, Summary>,
}

pub type Outcome = (Value, Option<(&'static str, Value)>);

fn summarise(
    id: &str,
    world: &World,
    created_ms: u64,
    now: u64,
    ensemble: Option<Ensemble>,
) -> Summary {
    let report = world.report();
    let spec = &world.state().spec;
    Summary {
        id: id.to_owned(),
        title: spec.title.clone(),
        question: spec.question.clone(),
        round: world.round(),
        rounds: spec.rounds,
        agents: report.agents,
        events: u32::try_from(spec.events.len()).unwrap_or(u32::MAX),
        leaning: report.outcome.leaning,
        mean: report.outcome.mean,
        polarization: report.outcome.polarization,
        created_ms,
        updated_ms: now,
        ensemble,
    }
}

impl Foresight {
    pub fn open(dir: PathBuf) -> Result<Self, AgencyError> {
        files::private_dir(&dir)?;
        let sealer = Sealer::new(files::load_key(&dir.join("foresight.key"))?);
        let index = match files::read(&dir.join(format!("{INDEX}.bin")))? {
            Some(bytes) => serde_json::from_slice(&sealer.open(INDEX, &bytes)?)?,
            None => BTreeMap::new(),
        };
        Ok(Self { dir, sealer, index })
    }

    fn path(&self, id: &str) -> PathBuf {
        self.dir.join(format!("{id}.bin"))
    }

    fn store_index(&self) -> Result<(), AgencyError> {
        let bytes = serde_json::to_vec(&self.index)?;
        files::write_atomic(
            &self.dir.join(format!("{INDEX}.bin")),
            &self.sealer.seal(INDEX, &bytes)?,
        )
    }

    fn summary(&self, id: &str) -> Result<&Summary, AgencyError> {
        self.index.get(id).ok_or(AgencyError::NotFound)
    }

    fn load(&self, id: &ProjectId) -> Result<World, AgencyError> {
        let key = id.as_str();
        self.summary(key)?;
        let bytes = files::read(&self.path(key))?.ok_or(AgencyError::NotFound)?;
        let plain = self.sealer.open(key, &bytes)?;
        let state: WorldState = serde_json::from_slice(&plain)?;
        Ok(World::restore(state)?)
    }

    fn save(
        &mut self,
        id: &ProjectId,
        world: &World,
        now: u64,
        ensemble: Option<Ensemble>,
    ) -> Result<Summary, AgencyError> {
        let key = id.as_str();
        let created = self.index.get(key).map_or(now, |s| s.created_ms);
        let kept = ensemble.or_else(|| self.index.get(key).and_then(|s| s.ensemble));
        let bytes = zeroize::Zeroizing::new(serde_json::to_vec(world.state())?);
        files::write_atomic(&self.path(key), &self.sealer.seal(key, &bytes)?)?;
        let summary = summarise(key, world, created, now, kept);
        self.index.insert(key.to_owned(), summary.clone());
        self.store_index()?;
        Ok(summary)
    }

    #[must_use]
    pub fn list(&self) -> Value {
        json!(self.index.values().collect::<Vec<_>>())
    }

    pub fn create(
        &mut self,
        id: &ProjectId,
        scenario: ScenarioSpec,
        now: u64,
    ) -> Result<Outcome, AgencyError> {
        if self.index.contains_key(id.as_str()) {
            return Err(AgencyError::Exists);
        }
        if self.index.len() >= MAX_SIMULATIONS {
            return Err(AgencyError::TooMany);
        }
        let world = World::new(scenario)?;
        let summary = self.save(id, &world, now, None)?;
        let event = json!({ "simulation": id, "agents": summary.agents, "rounds": summary.rounds });
        Ok((json!(summary), Some(("foresight.created", event))))
    }

    pub fn run(
        &mut self,
        id: &ProjectId,
        rounds: Option<u16>,
        now: u64,
    ) -> Result<Outcome, AgencyError> {
        let mut world = self.load(id)?;
        let agents = world.state().agents.len().max(1);
        let cap = u16::try_from(STEP_WORK.checked_div(agents).unwrap_or(1))
            .unwrap_or(u16::MAX)
            .max(1);
        let wanted = rounds.unwrap_or(cap).clamp(1, cap);
        let done = world.advance(wanted);
        let latest = world.latest().copied();
        let summary = self.save(id, &world, now, None)?;
        let event = (done > 0).then(|| {
            (
                "foresight.advanced",
                json!({ "simulation": id, "rounds": done, "round": summary.round }),
            )
        });
        Ok((
            json!({ "summary": summary, "advanced": done, "latest": latest, "finished": world.finished() }),
            event,
        ))
    }

    pub fn inject(
        &mut self,
        id: &ProjectId,
        event: EventSpec,
        now: u64,
    ) -> Result<Outcome, AgencyError> {
        let mut world = self.load(id)?;
        let round = event.round;
        world.inject(event)?;
        let summary = self.save(id, &world, now, None)?;
        Ok((
            json!(summary),
            Some((
                "foresight.injected",
                json!({ "simulation": id, "round": round }),
            )),
        ))
    }

    pub fn report(&self, id: &ProjectId) -> Result<Value, AgencyError> {
        let world = self.load(id)?;
        let summary = self.summary(id.as_str())?;
        Ok(json!({ "report": world.report(), "ensemble": summary.ensemble }))
    }

    pub fn agent(&self, id: &ProjectId, agent: &str) -> Result<Value, AgencyError> {
        let world = self.load(id)?;
        Ok(json!(world.agent(agent)?))
    }

    pub fn scenario(&self, id: &ProjectId) -> Result<ScenarioSpec, AgencyError> {
        Ok(self.load(id)?.into_state().spec)
    }

    pub fn record(
        &mut self,
        id: &ProjectId,
        ensemble: Ensemble,
        now: u64,
    ) -> Result<Outcome, AgencyError> {
        let world = self.load(id)?;
        let summary = self.save(id, &world, now, Some(ensemble))?;
        let event = json!({ "simulation": id, "runs": ensemble.runs });
        Ok((json!(summary), Some(("foresight.ensemble", event))))
    }

    pub fn delete(&mut self, id: &ProjectId) -> Result<Outcome, AgencyError> {
        let key = id.as_str();
        self.summary(key)?;
        match std::fs::remove_file(self.path(key)) {
            Ok(()) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.into()),
        }
        self.index.remove(key);
        self.store_index()?;
        Ok((
            json!({ "deleted": id }),
            Some(("foresight.deleted", json!({ "simulation": id }))),
        ))
    }
}
