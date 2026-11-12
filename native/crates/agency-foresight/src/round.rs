use crate::agent::{Memory, Recall};
use crate::dynamics::{Choice, Exposure, agreement, choose, update, weight};
use crate::feed::Draft;
use crate::spec::{MAX_FOLLOWS, Platform};
use crate::stats::{Activity, measure};
use crate::world::World;

const READ: usize = 6;

#[derive(Debug, Clone, Copy)]
enum Act {
    Publish {
        author: usize,
        platform: Platform,
        stance: f64,
        parent: Option<u64>,
    },
    Like {
        agent: usize,
        post: u64,
    },
    Repost {
        agent: usize,
        post: u64,
    },
    Follow {
        agent: usize,
        target: usize,
    },
    Unfollow {
        agent: usize,
        target: usize,
    },
}

fn bump(value: &mut u32) {
    *value = value.saturating_add(1);
}

impl World {
    pub(crate) fn step(&mut self) {
        let round = self.state.round.saturating_add(1);
        let n = self.state.agents.len();
        let mut exposures: Vec<Vec<Exposure>> = vec![Vec::new(); n];
        self.broadcast(round, &mut exposures);
        let feed_top = self.state.feed.trending(Platform::Feed, round);
        let forum_top = self.state.feed.trending(Platform::Forum, round);
        let mut acts = Vec::new();
        let mut activity = Activity::default();
        for (agent, seen) in exposures.iter_mut().enumerate() {
            let Some(traits) = self.state.spec.agents.get(agent).map(|a| a.traits) else {
                continue;
            };
            if self.state.rng.unit() >= traits.activity {
                continue;
            }
            bump(&mut activity.active);
            let platform = if self.state.rng.unit() < traits.forum {
                Platform::Forum
            } else {
                Platform::Feed
            };
            let top = match platform {
                Platform::Feed => &feed_top,
                Platform::Forum => &forum_top,
            };
            let read = self.read(agent, platform, round, top);
            self.react(agent, platform, &read, &mut acts);
            seen.extend(read);
        }
        self.absorb(round, &exposures);
        self.apply(round, acts, &mut activity);
        self.state.feed.prune(round);
        let stats = measure(round, &self.state.agents, activity);
        self.state.history.push(stats);
        self.state.round = round;
    }

    fn broadcast(&mut self, round: u16, exposures: &mut [Vec<Exposure>]) {
        let state = &mut self.state;
        for (index, event) in state.spec.events.iter().enumerate() {
            if event.round != round {
                continue;
            }
            let target = event.target.as_deref().and_then(|t| self.topo.entity(t));
            let id = state.feed.publish(Draft {
                round,
                author: None,
                event: Some(index),
                platform: Platform::Feed,
                stance: event.shift,
                parent: None,
            });
            let strength = 0.5 + event.shift.abs();
            let mut reached: u32 = 0;
            for (agent, slot) in exposures.iter_mut().enumerate() {
                let chance = match target {
                    Some(t) if self.topo.touches(agent, t) => (event.reach * 2.0).min(1.0),
                    Some(_) => event.reach * 0.5,
                    None => event.reach,
                };
                if state.rng.unit() < chance {
                    slot.push(Exposure {
                        post: Some(id),
                        author: None,
                        event: Some(index),
                        stance: event.shift,
                        weight: strength,
                    });
                    bump(&mut reached);
                }
            }
            if let Some(total) = state.event_reach.get_mut(index) {
                *total = total.saturating_add(reached);
            }
        }
    }

    fn read(
        &self,
        agent: usize,
        platform: Platform,
        round: u16,
        top: &[(u64, f64)],
    ) -> Vec<Exposure> {
        let state = &self.state;
        let Some(me) = state.agents.get(agent) else {
            return Vec::new();
        };
        let mut ids: Vec<(u64, f64)> = top.to_vec();
        if platform == Platform::Feed {
            ids.extend(
                me.follows
                    .iter()
                    .filter_map(|f| state.feed.latest_of(*f))
                    .map(|p| (p.id, p.score(platform, round))),
            );
            ids.sort_unstable_by_key(|(id, _)| *id);
            ids.dedup_by_key(|(id, _)| *id);
        }
        let mut ranked: Vec<(f64, Exposure)> = ids
            .into_iter()
            .filter_map(|(id, score)| state.feed.get(id).map(|p| (p, score)))
            .filter(|(p, _)| p.author != Some(agent))
            .map(|(p, score)| {
                let followed = p.author.is_some_and(|a| me.follows.contains(&a));
                let affinity = p.author.map_or(0.0, |a| self.topo.affinity(agent, a));
                let influence = p
                    .author
                    .and_then(|a| state.spec.agents.get(a))
                    .map_or(0.8, |s| s.traits.influence);
                let boost = if followed { 1.5 } else { 0.0 };
                let exposure = Exposure {
                    post: Some(p.id),
                    author: p.author,
                    event: p.event,
                    stance: p.stance,
                    weight: weight(influence, followed, affinity),
                };
                (score + boost + 0.8 * affinity, exposure)
            })
            .collect();
        if ranked.len() > READ {
            ranked.select_nth_unstable_by(READ, |a, b| b.0.total_cmp(&a.0));
            ranked.truncate(READ);
        }
        ranked.into_iter().map(|(_, e)| e).collect()
    }

    fn react(&mut self, agent: usize, platform: Platform, read: &[Exposure], acts: &mut Vec<Act>) {
        let Some(me) = self.state.agents.get(agent) else {
            return;
        };
        let stance = me.stance;
        let best = read.iter().copied().max_by(|a, b| {
            (a.weight * agreement(a.stance, stance))
                .total_cmp(&(b.weight * agreement(b.stance, stance)))
        });
        let rng = &mut self.state.rng;
        let agree = best.map_or(0.5, |e| agreement(e.stance, stance));
        let choice = match best {
            Some(_) => choose(rng, agree),
            None if rng.unit() < 0.5 => Choice::Post,
            None => Choice::Quiet,
        };
        let post = best.and_then(|e| e.post);
        let own = (stance + rng.jitter(0.05)).clamp(-1.0, 1.0);
        match (choice, post) {
            (Choice::Like, Some(post)) => acts.push(Act::Like { agent, post }),
            (Choice::Repost, Some(post)) => acts.push(Act::Repost { agent, post }),
            (Choice::Reply, Some(parent)) => acts.push(Act::Publish {
                author: agent,
                platform,
                stance: own,
                parent: Some(parent),
            }),
            (Choice::Post, _) => acts.push(Act::Publish {
                author: agent,
                platform,
                stance: own,
                parent: None,
            }),
            _ => {}
        }
        let Some(target) = best.and_then(|e| e.author) else {
            return;
        };
        let followed = me.follows.contains(&target);
        let roll = rng.unit();
        if !followed && agree > 0.9 && roll < 0.15 && me.follows.len() < MAX_FOLLOWS {
            acts.push(Act::Follow { agent, target });
        } else if followed && agree < 0.25 && roll < 0.2 {
            acts.push(Act::Unfollow { agent, target });
        }
    }

    fn absorb(&mut self, round: u16, exposures: &[Vec<Exposure>]) {
        let state = &mut self.state;
        for (agent, seen) in exposures.iter().enumerate() {
            for author in seen.iter().filter_map(|e| e.author) {
                if let Some(a) = state.agents.get_mut(author) {
                    a.stats.reach = a.stats.reach.saturating_add(1);
                }
            }
            let (Some(spec), Some(me)) =
                (state.spec.agents.get(agent), state.agents.get_mut(agent))
            else {
                continue;
            };
            me.stance = update(me.stance, &spec.traits, seen);
            if let Some(strongest) = seen.iter().max_by(|a, b| a.weight.total_cmp(&b.weight)) {
                me.remember(Memory {
                    round,
                    kind: if strongest.event.is_some() {
                        Recall::Event
                    } else {
                        Recall::Read
                    },
                    other: strongest.author,
                    event: strongest.event,
                    stance: strongest.stance,
                });
            }
        }
    }

    fn apply(&mut self, round: u16, acts: Vec<Act>, activity: &mut Activity) {
        for act in acts {
            match act {
                Act::Publish {
                    author,
                    platform,
                    stance,
                    parent,
                } => {
                    let replied = parent
                        .and_then(|p| self.state.feed.get(p))
                        .and_then(|p| p.author);
                    self.state.feed.publish(Draft {
                        round,
                        author: Some(author),
                        event: None,
                        platform,
                        stance,
                        parent,
                    });
                    let kind = if parent.is_some() {
                        bump(&mut activity.replies);
                        self.credit(replied);
                        Recall::Replied
                    } else {
                        bump(&mut activity.posts);
                        Recall::Posted
                    };
                    self.record(author, round, kind, replied, stance);
                }
                Act::Like { agent, post } | Act::Repost { agent, post } => {
                    let repost = matches!(act, Act::Repost { .. });
                    let Some(original) = self.state.feed.get_mut(post) else {
                        continue;
                    };
                    if repost {
                        bump(&mut original.reposts);
                    } else {
                        bump(&mut original.likes);
                    }
                    let (author, stance, event) =
                        (original.author, original.stance, original.event);
                    self.credit(author);
                    if repost {
                        bump(&mut activity.reposts);
                        self.state.feed.publish(Draft {
                            round,
                            author: Some(agent),
                            event,
                            platform: Platform::Feed,
                            stance,
                            parent: None,
                        });
                        self.record(agent, round, Recall::Reposted, author, stance);
                    } else {
                        bump(&mut activity.likes);
                        self.record(agent, round, Recall::Liked, author, stance);
                    }
                }
                Act::Follow { agent, target } | Act::Unfollow { agent, target } => {
                    let follow = matches!(act, Act::Follow { .. });
                    let Some(me) = self.state.agents.get_mut(agent) else {
                        continue;
                    };
                    let changed = if follow {
                        me.follows.len() < MAX_FOLLOWS && me.follows.insert(target)
                    } else {
                        me.follows.remove(&target)
                    };
                    if changed {
                        let kind = if follow {
                            Recall::Followed
                        } else {
                            Recall::Unfollowed
                        };
                        let stance = me.stance;
                        self.record(agent, round, kind, Some(target), stance);
                    }
                }
            }
        }
    }

    fn credit(&mut self, author: Option<usize>) {
        if let Some(a) = author.and_then(|a| self.state.agents.get_mut(a)) {
            bump(&mut a.stats.engagement);
        }
    }

    fn record(
        &mut self,
        agent: usize,
        round: u16,
        kind: Recall,
        other: Option<usize>,
        stance: f64,
    ) {
        let Some(me) = self.state.agents.get_mut(agent) else {
            return;
        };
        match kind {
            Recall::Posted => bump(&mut me.stats.posts),
            Recall::Replied => bump(&mut me.stats.replies),
            Recall::Reposted => bump(&mut me.stats.reposts),
            Recall::Liked => bump(&mut me.stats.likes),
            _ => {}
        }
        me.remember(Memory {
            round,
            kind,
            other,
            event: None,
            stance,
        });
    }
}
