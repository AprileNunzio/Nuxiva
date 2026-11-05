use serde::{Deserialize, Serialize};

use crate::agent::AgentState;
use crate::error::ForesightError;
use crate::feed::Feed;
use crate::rng::Rng;
use crate::spec::{EventSpec, MAX_EVENTS, MAX_FOLLOWS, ScenarioSpec};
use crate::stats::{Activity, RoundStats, measure};
use crate::topology::Topology;

pub const MAX_WORK: u64 = 960_000;
const PEER_FOLLOWS: usize = 24;
const HUBS: usize = 32;
const BOOTSTRAP: usize = 3;
const PEER_AFFINITY: f64 = 0.5;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorldState {
    pub spec: ScenarioSpec,
    pub(crate) rng: Rng,
    pub round: u16,
    pub agents: Vec<AgentState>,
    pub feed: Feed,
    pub history: Vec<RoundStats>,
    pub event_reach: Vec<u32>,
}

#[derive(Debug, Clone)]
pub struct World {
    pub(crate) state: WorldState,
    pub(crate) topo: Topology,
}

pub(crate) fn work(spec: &ScenarioSpec) -> Result<u64, ForesightError> {
    let agents = u64::try_from(spec.agents.len()).map_err(|_| ForesightError::Limit("work"))?;
    let total = agents
        .checked_mul(u64::from(spec.rounds))
        .ok_or(ForesightError::Limit("work"))?;
    if total > MAX_WORK {
        return Err(ForesightError::Limit("work"));
    }
    Ok(total)
}

fn follow(agents: &mut [AgentState], who: usize, target: usize) {
    if who == target {
        return;
    }
    if let Some(agent) = agents.get_mut(who) {
        if agent.follows.len() < MAX_FOLLOWS {
            agent.follows.insert(target);
        }
    }
}

fn wire(spec: &ScenarioSpec, topo: &Topology, rng: &mut Rng, agents: &mut [AgentState]) {
    for (who, agent) in spec.agents.iter().enumerate() {
        for target in agent.follows.iter().filter_map(|k| topo.agent(k)) {
            follow(agents, who, target);
        }
        let Some(entity) = topo.entity_of(who) else {
            continue;
        };
        let mut peers: Vec<usize> = topo.members(entity).to_vec();
        for &(other, weight) in topo.related(entity) {
            if weight >= PEER_AFFINITY {
                peers.extend_from_slice(topo.members(other));
            }
        }
        peers.retain(|&p| p != who);
        for _ in 0..PEER_FOLLOWS.min(peers.len()) {
            let pick = rng.below(peers.len());
            if pick < peers.len() {
                let target = peers.swap_remove(pick);
                follow(agents, who, target);
            }
        }
    }
    let mut hubs: Vec<usize> = (0..spec.agents.len()).collect();
    hubs.sort_by(|a, b| {
        let ia = spec.agents.get(*a).map_or(0.0, |s| s.traits.influence);
        let ib = spec.agents.get(*b).map_or(0.0, |s| s.traits.influence);
        ib.total_cmp(&ia).then(a.cmp(b))
    });
    hubs.truncate(HUBS);
    for who in 0..agents.len() {
        if agents.get(who).is_some_and(|a| a.follows.is_empty()) {
            for _ in 0..BOOTSTRAP {
                if let Some(&target) = hubs.get(rng.below(hubs.len())) {
                    follow(agents, who, target);
                }
            }
        }
    }
}

impl World {
    pub fn new(spec: ScenarioSpec) -> Result<Self, ForesightError> {
        spec.validate()?;
        work(&spec)?;
        let topo = Topology::build(&spec)?;
        let mut rng = Rng::new(spec.seed);
        let mut agents: Vec<AgentState> = spec
            .agents
            .iter()
            .map(|a| AgentState::new(a.traits.stance))
            .collect();
        wire(&spec, &topo, &mut rng, &mut agents);
        let first = measure(0, &agents, Activity::default());
        let event_reach = vec![0; spec.events.len()];
        Ok(Self {
            state: WorldState {
                spec,
                rng,
                round: 0,
                agents,
                feed: Feed::default(),
                history: vec![first],
                event_reach,
            },
            topo,
        })
    }

    pub fn restore(state: WorldState) -> Result<Self, ForesightError> {
        state.spec.validate()?;
        work(&state.spec)?;
        let n = state.spec.agents.len();
        let consistent = state.agents.len() == n
            && state.round <= state.spec.rounds
            && state.event_reach.len() == state.spec.events.len()
            && state.history.len() == usize::from(state.round).saturating_add(1)
            && state.feed.valid()
            && state.agents.iter().all(|a| {
                a.stance.is_finite()
                    && a.initial.is_finite()
                    && (-1.0..=1.0).contains(&a.stance)
                    && a.follows.len() <= MAX_FOLLOWS
                    && a.follows.iter().all(|&f| f < n)
            });
        if !consistent {
            return Err(ForesightError::Corrupt);
        }
        let topo = Topology::build(&state.spec)?;
        Ok(Self { state, topo })
    }

    #[must_use]
    pub fn state(&self) -> &WorldState {
        &self.state
    }

    #[must_use]
    pub fn into_state(self) -> WorldState {
        self.state
    }

    #[must_use]
    pub fn round(&self) -> u16 {
        self.state.round
    }

    #[must_use]
    pub fn finished(&self) -> bool {
        self.state.round >= self.state.spec.rounds
    }

    #[must_use]
    pub fn latest(&self) -> Option<&RoundStats> {
        self.state.history.last()
    }

    pub fn advance(&mut self, rounds: u16) -> u16 {
        let mut done: u16 = 0;
        while done < rounds && !self.finished() {
            self.step();
            done = done.saturating_add(1);
        }
        done
    }

    pub fn inject(&mut self, event: EventSpec) -> Result<(), ForesightError> {
        if self.finished() {
            return Err(ForesightError::Finished);
        }
        event.validate(self.state.spec.rounds)?;
        if event.round <= self.state.round {
            return Err(ForesightError::Invalid {
                field: "event round",
                reason: "already simulated",
            });
        }
        if event
            .target
            .as_deref()
            .is_some_and(|t| self.topo.entity(t).is_none())
        {
            return Err(ForesightError::Unknown("event target"));
        }
        if self.state.spec.events.len() >= MAX_EVENTS {
            return Err(ForesightError::Limit("events"));
        }
        self.state.spec.events.push(event);
        self.state.event_reach.push(0);
        Ok(())
    }
}
