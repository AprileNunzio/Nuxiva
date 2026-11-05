use std::collections::BTreeMap;

use crate::error::ForesightError;
use crate::spec::ScenarioSpec;

#[derive(Debug, Clone, Default)]
pub struct Topology {
    agents: BTreeMap<String, usize>,
    entities: BTreeMap<String, usize>,
    agent_entity: Vec<Option<usize>>,
    relations: BTreeMap<(usize, usize), f64>,
    members: Vec<Vec<usize>>,
    related: Vec<Vec<(usize, f64)>>,
}

fn pair(a: usize, b: usize) -> (usize, usize) {
    if a <= b { (a, b) } else { (b, a) }
}

impl Topology {
    pub fn build(spec: &ScenarioSpec) -> Result<Self, ForesightError> {
        let entities: BTreeMap<String, usize> = spec
            .entities
            .iter()
            .enumerate()
            .map(|(i, e)| (e.key.clone(), i))
            .collect();
        let agents: BTreeMap<String, usize> = spec
            .agents
            .iter()
            .enumerate()
            .map(|(i, a)| (a.key.clone(), i))
            .collect();
        let mut relations = BTreeMap::new();
        for relation in &spec.relations {
            let from = *entities
                .get(&relation.from)
                .ok_or(ForesightError::Unknown("relations"))?;
            let to = *entities
                .get(&relation.to)
                .ok_or(ForesightError::Unknown("relations"))?;
            if relations.insert(pair(from, to), relation.weight).is_some() {
                return Err(ForesightError::Duplicate("relations"));
            }
        }
        let agent_entity: Vec<Option<usize>> = spec
            .agents
            .iter()
            .map(|a| a.entity.as_ref().and_then(|e| entities.get(e).copied()))
            .collect();
        let mut members = vec![Vec::new(); entities.len()];
        for (agent, entity) in agent_entity.iter().enumerate() {
            if let Some(list) = entity.and_then(|e| members.get_mut(e)) {
                list.push(agent);
            }
        }
        let mut related = vec![Vec::new(); entities.len()];
        for (&(a, b), &w) in &relations {
            if let Some(list) = related.get_mut(a) {
                list.push((b, w));
            }
            if let Some(list) = related.get_mut(b) {
                list.push((a, w));
            }
        }
        Ok(Self {
            agents,
            entities,
            agent_entity,
            relations,
            members,
            related,
        })
    }

    #[must_use]
    pub fn agent(&self, key: &str) -> Option<usize> {
        self.agents.get(key).copied()
    }

    #[must_use]
    pub fn entity(&self, key: &str) -> Option<usize> {
        self.entities.get(key).copied()
    }

    #[must_use]
    pub fn entity_of(&self, agent: usize) -> Option<usize> {
        self.agent_entity.get(agent).copied().flatten()
    }

    #[must_use]
    pub fn entity_affinity(&self, a: usize, b: usize) -> f64 {
        if a == b {
            return 1.0;
        }
        self.relations.get(&pair(a, b)).copied().unwrap_or(0.0)
    }

    #[must_use]
    pub fn affinity(&self, a: usize, b: usize) -> f64 {
        match (self.entity_of(a), self.entity_of(b)) {
            (Some(x), Some(y)) => self.entity_affinity(x, y),
            _ => 0.0,
        }
    }

    #[must_use]
    pub fn touches(&self, agent: usize, target: usize) -> bool {
        self.entity_of(agent)
            .is_some_and(|e| e == target || self.entity_affinity(e, target).abs() > 0.0)
    }

    #[must_use]
    pub fn members(&self, entity: usize) -> &[usize] {
        self.members.get(entity).map_or(&[], Vec::as_slice)
    }

    #[must_use]
    pub fn related(&self, entity: usize) -> &[(usize, f64)] {
        self.related.get(entity).map_or(&[], Vec::as_slice)
    }
}
