use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::feed::Post;
use crate::num::{count, mean, round3};
use crate::spec::Platform;
use crate::stats::{RoundStats, histogram};
use crate::world::World;

const TOP: usize = 10;
const MOMENTUM_SHARE: usize = 10;
const DIVIDED: f64 = 0.6;
const MARGIN: f64 = 0.1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Leaning {
    Support,
    Oppose,
    Divided,
    Undecided,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Outcome {
    pub leaning: Leaning,
    pub mean: f64,
    pub support: f64,
    pub oppose: f64,
    pub neutral: f64,
    pub polarization: f64,
    pub momentum: f64,
    pub shift: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentBrief {
    pub key: String,
    pub name: String,
    pub role: String,
    pub stance: f64,
    pub initial: f64,
    pub reach: u64,
    pub engagement: u32,
    pub followers: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GroupStat {
    pub label: String,
    pub count: u32,
    pub initial: f64,
    pub current: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EventImpact {
    pub round: u16,
    pub title: String,
    pub reached: u32,
    pub before: f64,
    pub after: f64,
    pub delta: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PostBrief {
    pub author: Option<String>,
    pub author_name: Option<String>,
    pub event: Option<String>,
    pub round: u16,
    pub platform: Platform,
    pub stance: f64,
    pub likes: u32,
    pub reposts: u32,
    pub replies: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Report {
    pub title: String,
    pub question: String,
    pub round: u16,
    pub rounds: u16,
    pub finished: bool,
    pub agents: u32,
    pub outcome: Outcome,
    pub histogram: Vec<u32>,
    pub trajectory: Vec<RoundStats>,
    pub influencers: Vec<AgentBrief>,
    pub movers: Vec<AgentBrief>,
    pub roles: Vec<GroupStat>,
    pub entities: Vec<GroupStat>,
    pub events: Vec<EventImpact>,
    pub notable: Vec<PostBrief>,
}

#[must_use]
pub fn leaning(stats: &RoundStats) -> Leaning {
    if stats.polarization >= DIVIDED {
        Leaning::Divided
    } else if stats.support - stats.oppose > MARGIN {
        Leaning::Support
    } else if stats.oppose - stats.support > MARGIN {
        Leaning::Oppose
    } else {
        Leaning::Undecided
    }
}

fn momentum(history: &[RoundStats]) -> f64 {
    let window = (history.len() / MOMENTUM_SHARE).max(1);
    let last = history.last().map_or(0.0, |s| s.mean);
    let start = history
        .len()
        .checked_sub(window.saturating_add(1))
        .and_then(|i| history.get(i))
        .or_else(|| history.first())
        .map_or(last, |s| s.mean);
    round3(last - start)
}

impl World {
    #[must_use]
    pub fn followers(&self) -> Vec<u32> {
        let mut out = vec![0_u32; self.state.agents.len()];
        for agent in &self.state.agents {
            for &target in &agent.follows {
                if let Some(slot) = out.get_mut(target) {
                    *slot = slot.saturating_add(1);
                }
            }
        }
        out
    }

    pub(crate) fn brief(&self, agent: usize, followers: &[u32]) -> Option<AgentBrief> {
        let spec = self.state.spec.agents.get(agent)?;
        let state = self.state.agents.get(agent)?;
        Some(AgentBrief {
            key: spec.key.clone(),
            name: spec.name.clone(),
            role: spec.role.clone(),
            stance: round3(state.stance),
            initial: round3(state.initial),
            reach: state.stats.reach,
            engagement: state.stats.engagement,
            followers: followers.get(agent).copied().unwrap_or(0),
        })
    }

    fn top_by(&self, followers: &[u32], key: impl Fn(usize) -> f64) -> Vec<AgentBrief> {
        let mut order: Vec<usize> = (0..self.state.agents.len()).collect();
        order.sort_by(|a, b| key(*b).total_cmp(&key(*a)).then(a.cmp(b)));
        order
            .into_iter()
            .take(TOP)
            .filter_map(|i| self.brief(i, followers))
            .collect()
    }

    fn groups(&self, label: impl Fn(usize) -> Option<String>) -> Vec<GroupStat> {
        let mut sums: BTreeMap<String, (usize, f64, f64)> = BTreeMap::new();
        for (i, agent) in self.state.agents.iter().enumerate() {
            if let Some(name) = label(i) {
                let entry = sums.entry(name).or_insert((0, 0.0, 0.0));
                entry.0 = entry.0.saturating_add(1);
                entry.1 += agent.initial;
                entry.2 += agent.stance;
            }
        }
        sums.into_iter()
            .map(|(label, (n, initial, current))| GroupStat {
                label,
                count: u32::try_from(n).unwrap_or(u32::MAX),
                initial: round3(mean(initial, n)),
                current: round3(mean(current, n)),
            })
            .collect()
    }

    fn impacts(&self) -> Vec<EventImpact> {
        let history = &self.state.history;
        self.state
            .spec
            .events
            .iter()
            .zip(&self.state.event_reach)
            .filter(|(e, _)| e.round <= self.state.round)
            .map(|(event, reached)| {
                let at = usize::from(event.round);
                let before = history.get(at.saturating_sub(1)).map_or(0.0, |s| s.mean);
                let after = history
                    .get(at.saturating_add(2))
                    .or_else(|| history.last())
                    .map_or(before, |s| s.mean);
                EventImpact {
                    round: event.round,
                    title: event.title.clone(),
                    reached: *reached,
                    before,
                    after,
                    delta: round3(after - before),
                }
            })
            .collect()
    }

    fn post_brief(&self, post: &Post) -> PostBrief {
        let author = post.author.and_then(|a| self.state.spec.agents.get(a));
        PostBrief {
            author: author.map(|a| a.key.clone()),
            author_name: author.map(|a| a.name.clone()),
            event: post
                .event
                .and_then(|e| self.state.spec.events.get(e))
                .map(|e| e.title.clone()),
            round: post.round,
            platform: post.platform,
            stance: round3(post.stance),
            likes: post.likes,
            reposts: post.reposts,
            replies: post.replies,
        }
    }

    #[must_use]
    pub fn report(&self) -> Report {
        let state = &self.state;
        let last = state.history.last().copied().unwrap_or_default();
        let first = state.history.first().copied().unwrap_or_default();
        let followers = self.followers();
        let agents = &state.agents;
        let influence = |i: usize| {
            agents.get(i).map_or(0.0, |a| {
                count(usize::try_from(a.stats.reach).unwrap_or(usize::MAX)).ln_1p()
                    + f64::from(a.stats.engagement).ln_1p() * 1.5
                    + f64::from(followers.get(i).copied().unwrap_or(0)).ln_1p()
            })
        };
        let moved = |i: usize| agents.get(i).map_or(0.0, |a| (a.stance - a.initial).abs());
        Report {
            title: state.spec.title.clone(),
            question: state.spec.question.clone(),
            round: state.round,
            rounds: state.spec.rounds,
            finished: self.finished(),
            agents: u32::try_from(agents.len()).unwrap_or(u32::MAX),
            outcome: Outcome {
                leaning: leaning(&last),
                mean: last.mean,
                support: last.support,
                oppose: last.oppose,
                neutral: last.neutral,
                polarization: last.polarization,
                momentum: momentum(&state.history),
                shift: round3(last.mean - first.mean),
            },
            histogram: histogram(agents),
            trajectory: state.history.clone(),
            influencers: self.top_by(&followers, influence),
            movers: self.top_by(&followers, moved),
            roles: self.groups(|i| state.spec.agents.get(i).map(|a| a.role.clone())),
            entities: self.groups(|i| {
                state
                    .spec
                    .agents
                    .get(i)
                    .and_then(|a| a.entity.as_ref())
                    .and_then(|k| state.spec.entities.iter().find(|e| &e.key == k))
                    .map(|e| e.name.clone())
            }),
            events: self.impacts(),
            notable: state
                .feed
                .notable()
                .iter()
                .map(|p| self.post_brief(p))
                .collect(),
        }
    }
}
