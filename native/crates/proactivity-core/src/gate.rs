use std::collections::{BTreeMap, BTreeSet, VecDeque};

use serde::{Deserialize, Serialize};

use crate::clock::HOUR_MS;
use crate::model::{Context, Domain, Privacy};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Gate {
    Allow,
    Redact,
    Block,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PersonPolicy {
    #[serde(default)]
    pub muted: BTreeSet<Domain>,
    #[serde(default)]
    pub sealed: BTreeSet<Domain>,
}

#[must_use]
pub fn effective(declared: Privacy, domain: Domain, policy: Option<&PersonPolicy>) -> Privacy {
    let floor = match domain {
        Domain::Health | Domain::Email => Privacy::Private,
        Domain::Security => Privacy::Household,
        _ => Privacy::Public,
    };
    let sealed = policy.is_some_and(|p| p.sealed.contains(&domain));
    let level = declared.max(floor);
    if sealed { Privacy::Private } else { level }
}

#[must_use]
pub fn gate(privacy: Privacy, target: Option<&str>, ctx: &Context) -> Gate {
    match privacy {
        Privacy::Public => Gate::Allow,
        Privacy::Household => {
            if ctx.guests_present {
                Gate::Redact
            } else {
                Gate::Allow
            }
        }
        Privacy::Private => {
            let alone = !ctx.guests_present
                && ctx.present.len() == 1
                && target.is_some_and(|t| ctx.present.first().is_some_and(|p| p == t));
            if alone { Gate::Allow } else { Gate::Block }
        }
    }
}

#[derive(Debug, Default)]
pub struct Interruptions {
    global: VecDeque<u64>,
    people: BTreeMap<String, VecDeque<u64>>,
}

fn prune(queue: &mut VecDeque<u64>, now: u64) {
    while queue
        .front()
        .is_some_and(|t| now.saturating_sub(*t) >= HOUR_MS)
    {
        queue.pop_front();
    }
}

impl Interruptions {
    pub fn global(&mut self, now: u64) -> usize {
        prune(&mut self.global, now);
        self.global.len()
    }

    pub fn person(&mut self, person: Option<&str>, now: u64) -> usize {
        let Some(name) = person else { return 0 };
        self.people.get_mut(name).map_or(0, |q| {
            prune(q, now);
            q.len()
        })
    }

    pub fn charge(&mut self, person: Option<&str>, now: u64) {
        self.global.push_back(now);
        if let Some(name) = person {
            if self.people.len() < 1_024 || self.people.contains_key(name) {
                self.people
                    .entry(name.to_owned())
                    .or_default()
                    .push_back(now);
            }
        }
        self.people.retain(|_, q| {
            prune(q, now);
            !q.is_empty()
        });
    }
}
