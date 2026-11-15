use crate::error::{PeerError, PeerResult};
use crate::job::JobSpec;
use crate::registry::Registry;
use crate::score::{Needed, Reserved, eligible, needed, score};
use std::collections::BTreeMap;

pub const MAX_JOBS: usize = 4096;
const MAX_EXCLUDED: usize = 8;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Phase {
    Pending,
    Assigned { node: String, lease_until: i64 },
    Done,
    Failed(Reason),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    NoCapacity,
    Attempts,
    Deadline,
}

impl Reason {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::NoCapacity => "peer.job.no_capacity",
            Self::Attempts => "peer.job.attempts",
            Self::Deadline => "peer.job.deadline",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decision {
    Assign {
        job: u64,
        node: String,
        lease_until: i64,
        attempt: u8,
        degraded: bool,
    },
    Failed {
        job: u64,
        reason: Reason,
    },
}

#[derive(Debug, Clone)]
struct State {
    spec: JobSpec,
    phase: Phase,
    attempts: u8,
    excluded: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct Scheduler {
    jobs: BTreeMap<u64, State>,
}

impl Scheduler {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn submit(&mut self, spec: JobSpec) -> PeerResult<bool> {
        spec.validate()?;
        if self.jobs.contains_key(&spec.id) {
            return Ok(false);
        }
        if self.jobs.len() >= MAX_JOBS {
            self.evict_finished();
            if self.jobs.len() >= MAX_JOBS {
                return Err(PeerError::Capacity);
            }
        }
        self.jobs.insert(
            spec.id,
            State {
                spec,
                phase: Phase::Pending,
                attempts: 0,
                excluded: Vec::new(),
            },
        );
        Ok(true)
    }

    fn evict_finished(&mut self) {
        let finished: Vec<u64> = self
            .jobs
            .iter()
            .filter(|(_, s)| matches!(s.phase, Phase::Done | Phase::Failed(_)))
            .map(|(id, _)| *id)
            .take(MAX_JOBS / 4)
            .collect();
        for id in finished {
            self.jobs.remove(&id);
        }
    }

    #[must_use]
    pub fn phase(&self, job: u64) -> Option<&Phase> {
        self.jobs.get(&job).map(|s| &s.phase)
    }

    #[must_use]
    pub fn is_idle(&self) -> bool {
        self.jobs
            .values()
            .all(|s| matches!(s.phase, Phase::Done | Phase::Failed(_)))
    }

    #[must_use]
    pub fn pending(&self) -> usize {
        self.jobs
            .values()
            .filter(|s| s.phase == Phase::Pending)
            .count()
    }

    #[must_use]
    pub fn assigned_to(&self, node: &str) -> usize {
        self.jobs
            .values()
            .filter(|s| matches!(&s.phase, Phase::Assigned { node: n, .. } if n == node))
            .count()
    }

    pub fn renew(&mut self, job: u64, node: &str, now: i64) -> PeerResult<i64> {
        let state = self.jobs.get_mut(&job).ok_or(PeerError::Unknown)?;
        match &mut state.phase {
            Phase::Assigned {
                node: n,
                lease_until,
            } if n == node => {
                *lease_until = now.saturating_add(i64::from(state.spec.lease_ms));
                Ok(*lease_until)
            }
            _ => Err(PeerError::State),
        }
    }

    pub fn complete(&mut self, job: u64, node: &str) -> PeerResult<()> {
        let state = self.jobs.get_mut(&job).ok_or(PeerError::Unknown)?;
        match &state.phase {
            Phase::Assigned { node: n, .. } if n == node => {
                state.phase = Phase::Done;
                Ok(())
            }
            _ => Err(PeerError::State),
        }
    }

    pub fn fail(&mut self, job: u64, node: &str) -> PeerResult<Option<Decision>> {
        let state = self.jobs.get_mut(&job).ok_or(PeerError::Unknown)?;
        match &state.phase {
            Phase::Assigned { node: n, .. } if n == node => Ok(Self::release(job, state, node)),
            _ => Err(PeerError::State),
        }
    }

    fn release(job: u64, state: &mut State, node: &str) -> Option<Decision> {
        if state.excluded.len() < MAX_EXCLUDED && !state.excluded.iter().any(|n| n == node) {
            state.excluded.push(node.to_owned());
        }
        if state.attempts >= state.spec.max_attempts {
            state.phase = Phase::Failed(Reason::Attempts);
            return Some(Decision::Failed {
                job,
                reason: Reason::Attempts,
            });
        }
        state.phase = Phase::Pending;
        None
    }

    fn reservations(&self) -> BTreeMap<String, Reserved> {
        let mut map: BTreeMap<String, Reserved> = BTreeMap::new();
        for state in self.jobs.values() {
            if let Phase::Assigned { node, .. } = &state.phase {
                let need = needed(&state.spec, false);
                let slot = map.entry(node.clone()).or_default();
                slot.cores = slot.cores.saturating_add(need.cores);
                slot.ram_mb = slot.ram_mb.saturating_add(need.ram_mb);
                slot.vram_mb = slot.vram_mb.saturating_add(need.vram_mb);
                slot.jobs = slot.jobs.saturating_add(1);
            }
        }
        map
    }

    fn pick(
        registry: &Registry,
        state: &State,
        reserved: &BTreeMap<String, Reserved>,
        need: &Needed,
    ) -> Option<String> {
        let empty = Reserved::default();
        if let Some(pref) = state.spec.affinity.as_deref() {
            if !state.excluded.iter().any(|n| n == pref) {
                if let Some(entry) = registry.get(pref) {
                    let held = reserved.get(pref).unwrap_or(&empty);
                    if eligible(entry, &state.spec, held, need) {
                        return Some(pref.to_owned());
                    }
                }
            }
        }
        let mut best: Option<(u64, &String)> = None;
        for (id, entry) in registry.alive() {
            if state.excluded.iter().any(|n| n == id) {
                continue;
            }
            let held = reserved.get(id).unwrap_or(&empty);
            if !eligible(entry, &state.spec, held, need) {
                continue;
            }
            let value = score(id, entry, &state.spec, held);
            let better = match best {
                None => true,
                Some((top, top_id)) => value > top || (value == top && id < top_id),
            };
            if better {
                best = Some((value, id));
            }
        }
        best.map(|(_, id)| id.clone())
    }

    pub fn tick(&mut self, registry: &Registry, now: i64) -> Vec<Decision> {
        let mut decisions = Vec::new();
        let broken: Vec<u64> = self
            .jobs
            .iter()
            .filter_map(|(id, s)| match &s.phase {
                Phase::Assigned { node, lease_until } => {
                    let dead = registry
                        .get(node)
                        .is_none_or(|e| e.status == crate::registry::Status::Dead);
                    (dead || now >= *lease_until).then_some(*id)
                }
                _ => None,
            })
            .collect();
        for id in broken {
            if let Some(state) = self.jobs.get_mut(&id) {
                if let Phase::Assigned { node, .. } = state.phase.clone() {
                    if let Some(decision) = Self::release(id, state, &node) {
                        decisions.push(decision);
                    }
                }
            }
        }
        let mut reserved = self.reservations();
        let mut order: Vec<(u8, u64)> = self
            .jobs
            .iter()
            .filter(|(_, s)| s.phase == Phase::Pending)
            .map(|(id, s)| (s.spec.priority, *id))
            .collect();
        order.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
        for (_, id) in order {
            let Some(state) = self.jobs.get_mut(&id) else {
                continue;
            };
            if state.spec.deadline_ms > 0 && now >= state.spec.deadline_ms {
                state.phase = Phase::Failed(Reason::Deadline);
                decisions.push(Decision::Failed {
                    job: id,
                    reason: Reason::Deadline,
                });
                continue;
            }
            let strict = needed(&state.spec, false);
            let mut chosen =
                Self::pick(registry, state, &reserved, &strict).map(|n| (n, false, strict));
            if chosen.is_none() {
                let relaxed = needed(&state.spec, true);
                chosen =
                    Self::pick(registry, state, &reserved, &relaxed).map(|n| (n, true, relaxed));
            }
            let Some((node, degraded, need)) = chosen else {
                if state.spec.deadline_ms == 0 && state.attempts >= state.spec.max_attempts {
                    state.phase = Phase::Failed(Reason::NoCapacity);
                    decisions.push(Decision::Failed {
                        job: id,
                        reason: Reason::NoCapacity,
                    });
                }
                continue;
            };
            let lease_until = now.saturating_add(i64::from(state.spec.lease_ms));
            state.attempts = state.attempts.saturating_add(1);
            state.phase = Phase::Assigned {
                node: node.clone(),
                lease_until,
            };
            let slot = reserved.entry(node.clone()).or_default();
            slot.cores = slot.cores.saturating_add(need.cores);
            slot.ram_mb = slot.ram_mb.saturating_add(need.ram_mb);
            slot.vram_mb = slot.vram_mb.saturating_add(need.vram_mb);
            slot.jobs = slot.jobs.saturating_add(1);
            decisions.push(Decision::Assign {
                job: id,
                node,
                lease_until,
                attempt: state.attempts,
                degraded,
            });
        }
        decisions
    }
}
