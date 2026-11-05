use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

use crate::spec::Platform;

pub const WINDOW: u16 = 3;
pub const TRENDING: usize = 24;
const SHOWCASE: usize = 12;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Post {
    pub id: u64,
    pub round: u16,
    pub author: Option<usize>,
    pub event: Option<usize>,
    pub platform: Platform,
    pub stance: f64,
    pub parent: Option<u64>,
    pub likes: u32,
    pub reposts: u32,
    pub replies: u32,
}

#[derive(Debug, Clone, Copy)]
pub struct Draft {
    pub round: u16,
    pub author: Option<usize>,
    pub event: Option<usize>,
    pub platform: Platform,
    pub stance: f64,
    pub parent: Option<u64>,
}

impl Post {
    #[must_use]
    pub fn engagement(&self) -> u32 {
        self.likes
            .saturating_add(self.reposts.saturating_mul(2))
            .saturating_add(self.replies.saturating_mul(2))
    }

    #[must_use]
    pub fn score(&self, platform: Platform, round: u16) -> f64 {
        let age = f64::from(round.saturating_sub(self.round));
        let heat = f64::from(self.engagement()).ln_1p();
        let base = match platform {
            Platform::Feed => heat * 0.6 + 1.5 / (1.0 + age),
            Platform::Forum => f64::from(self.replies).ln_1p() * 1.2 + heat * 0.3 - age * 0.4,
        };
        if self.event.is_some() {
            base + 2.0
        } else {
            base
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Feed {
    posts: VecDeque<Post>,
    latest: Vec<Option<u64>>,
    base: u64,
    next: u64,
    showcase: Vec<Post>,
}

impl Feed {
    pub fn publish(&mut self, draft: Draft) -> u64 {
        let id = self.next;
        self.next = self.next.saturating_add(1);
        if let Some(author) = draft.author {
            if self.latest.len() <= author {
                self.latest.resize(author.saturating_add(1), None);
            }
            if let Some(slot) = self.latest.get_mut(author) {
                *slot = Some(id);
            }
        }
        if let Some(parent) = draft.parent.and_then(|p| self.get_mut(p)) {
            parent.replies = parent.replies.saturating_add(1);
        }
        self.posts.push_back(Post {
            id,
            round: draft.round,
            author: draft.author,
            event: draft.event,
            platform: draft.platform,
            stance: draft.stance,
            parent: draft.parent,
            likes: 0,
            reposts: 0,
            replies: 0,
        });
        id
    }

    #[must_use]
    pub fn get(&self, id: u64) -> Option<&Post> {
        let offset = usize::try_from(id.checked_sub(self.base)?).ok()?;
        self.posts.get(offset)
    }

    pub fn get_mut(&mut self, id: u64) -> Option<&mut Post> {
        let offset = usize::try_from(id.checked_sub(self.base)?).ok()?;
        self.posts.get_mut(offset)
    }

    #[must_use]
    pub fn latest_of(&self, author: usize) -> Option<&Post> {
        self.latest
            .get(author)
            .copied()
            .flatten()
            .and_then(|id| self.get(id))
    }

    #[must_use]
    pub fn trending(&self, platform: Platform, round: u16) -> Vec<(u64, f64)> {
        let mut ranked: Vec<(f64, u64)> = self
            .posts
            .iter()
            .filter(|p| p.platform == platform)
            .filter(|p| platform == Platform::Feed || p.parent.is_none())
            .map(|p| (p.score(platform, round), p.id))
            .collect();
        ranked.sort_by(|a, b| b.0.total_cmp(&a.0).then(a.1.cmp(&b.1)));
        ranked.truncate(TRENDING);
        ranked.into_iter().map(|(score, id)| (id, score)).collect()
    }

    pub fn prune(&mut self, round: u16) {
        while self
            .posts
            .front()
            .is_some_and(|p| p.round.saturating_add(WINDOW) <= round)
        {
            if let Some(post) = self.posts.pop_front() {
                self.base = post.id.saturating_add(1);
                self.keep(post);
            }
        }
        let base = self.base;
        for slot in &mut self.latest {
            if slot.is_some_and(|id| id < base) {
                *slot = None;
            }
        }
    }

    pub fn valid(&self) -> bool {
        let ordered = self
            .posts
            .iter()
            .zip(self.base..)
            .all(|(p, id)| p.id == id && p.stance.is_finite());
        let count = u64::try_from(self.posts.len()).unwrap_or(u64::MAX);
        ordered && self.base.checked_add(count) == Some(self.next)
    }

    fn keep(&mut self, post: Post) {
        if post.engagement() == 0 {
            return;
        }
        self.showcase.push(post);
        rank(&mut self.showcase);
        self.showcase.truncate(SHOWCASE);
    }

    #[must_use]
    pub fn notable(&self) -> Vec<Post> {
        let mut all: Vec<Post> = self
            .showcase
            .iter()
            .copied()
            .chain(self.posts.iter().copied().filter(|p| p.engagement() > 0))
            .collect();
        rank(&mut all);
        all.truncate(SHOWCASE);
        all
    }

    #[must_use]
    pub fn live(&self) -> usize {
        self.posts.len()
    }
}

fn rank(posts: &mut [Post]) {
    posts.sort_by(|a, b| b.engagement().cmp(&a.engagement()).then(a.id.cmp(&b.id)));
}
