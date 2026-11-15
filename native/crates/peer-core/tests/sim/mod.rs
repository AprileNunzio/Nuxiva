#![allow(clippy::pedantic)]
#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::match_wildcard_for_single_variants,
    clippy::cast_possible_truncation,
    dead_code
)]

mod node;

use nuxiva_peer_core::capability::Roles;
use nuxiva_peer_core::*;
use std::collections::{BTreeMap, BTreeSet};

pub use node::SimNode;

pub struct Rng(pub u64);

impl Rng {
    pub fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    pub fn below(&mut self, n: u64) -> u64 {
        self.next() % n.max(1)
    }
}

pub struct Delivery {
    pub to: usize,
    pub via: Option<usize>,
    pub env: Envelope,
}

#[derive(Default)]
pub struct Stats {
    pub done: BTreeSet<u64>,
    pub failed: BTreeSet<u64>,
    pub executed: BTreeMap<u64, Vec<usize>>,
    pub durations: BTreeMap<u64, i64>,
    pub rejected: BTreeMap<&'static str, u64>,
}

pub struct Sim {
    pub nodes: Vec<SimNode>,
    pub ids: Vec<String>,
    pub index: BTreeMap<String, usize>,
    pub queue: BTreeMap<(i64, u64), Delivery>,
    pub now: i64,
    pub counter: u64,
    pub rng: Rng,
    pub stats: Stats,
    pub next_job: u64,
    pub tap: Vec<Envelope>,
}

fn capabilities(index: usize, rng: &mut Rng) -> Capabilities {
    let roles = Roles {
        display: true,
        compute: true,
        coordinate: true,
    };
    match index {
        0 => Capabilities {
            tier: Tier::Server,
            roles,
            cpu_cores: 16,
            cpu_score: 9000,
            ram_mb: 32_768,
            gpu_vram_mb: 0,
            gpu_score: 0,
            battery_pct: None,
            charging: false,
            uplink_kbps: 1_000_000,
            rtt_ms: 1,
        },
        1..=20 => Capabilities {
            tier: Tier::Desktop,
            roles,
            cpu_cores: 8,
            cpu_score: 5000,
            ram_mb: 16_384,
            gpu_vram_mb: if index % 2 == 0 { 4096 } else { 0 },
            gpu_score: if index % 2 == 0 { 6000 } else { 0 },
            battery_pct: None,
            charging: false,
            uplink_kbps: 500_000,
            rtt_ms: 3,
        },
        _ => Capabilities {
            tier: Tier::Mobile,
            roles,
            cpu_cores: 8,
            cpu_score: 2500,
            ram_mb: 6144,
            gpu_vram_mb: 2048,
            gpu_score: 3500,
            battery_pct: Some(u8::try_from(10 + rng.below(91)).unwrap_or(50)),
            charging: rng.below(5) == 0,
            uplink_kbps: 50_000,
            rtt_ms: 25,
        },
    }
}

impl Sim {
    pub fn new(count: usize, seed: u64) -> Self {
        let mut rng = Rng(seed);
        let keys: Vec<PeerKey> = (0..count)
            .map(|i| {
                let mut s = [0u8; 32];
                s[..8].copy_from_slice(&(i as u64 + 1).to_be_bytes());
                s[8..16].copy_from_slice(&seed.to_be_bytes());
                PeerKey::from_seed(&s).expect("key")
            })
            .collect();
        let ids: Vec<String> = keys.iter().map(|k| k.id().to_owned()).collect();
        let index = ids
            .iter()
            .cloned()
            .enumerate()
            .map(|(i, id)| (id, i))
            .collect();
        let nodes = keys
            .into_iter()
            .enumerate()
            .map(|(i, key)| {
                let mut trust = TrustBook::new();
                for id in &ids {
                    trust.enroll(id).expect("enroll");
                }
                SimNode::new(
                    key,
                    trust,
                    capabilities(i, &mut rng),
                    rng.below(1000) as i64,
                )
            })
            .collect();
        Self {
            nodes,
            ids,
            index,
            queue: BTreeMap::new(),
            now: 0,
            counter: 0,
            rng,
            stats: Stats::default(),
            next_job: 1,
            tap: Vec::new(),
        }
    }

    pub fn enqueue(&mut self, to: usize, via: Option<usize>, env: Envelope) {
        let latency = 20 + self.rng.below(60) as i64;
        self.counter += 1;
        self.queue.insert(
            (self.now + latency, self.counter),
            Delivery { to, via, env },
        );
    }

    pub fn fan_out(&mut self, me: usize, env: &Envelope, via: Option<usize>) {
        if env.ttl == 0 {
            return;
        }
        let came = via.map(|v| self.ids[v].clone());
        let targets = self.nodes[me]
            .gossip
            .targets(&self.ids[me], env, came.as_deref(), &self.ids);
        let next = env.hop();
        for id in targets {
            let to = self.index[&id];
            self.nodes[me].sent += 1;
            self.nodes[to].received += 1;
            self.enqueue(to, Some(me), next.clone());
        }
    }

    pub fn emit(&mut self, me: usize, message: &Message, ttl: u8) {
        if !self.nodes[me].alive {
            return;
        }
        let env = self.nodes[me].seal(self.now, ttl, message);
        self.nodes[me].gossip.first_seen(&env);
        self.tap.push(env.clone());
        if self.tap.len() > 256 {
            self.tap.remove(0);
        }
        self.apply(me, &env, message);
        self.fan_out(me, &env, None);
    }

    pub fn reject(&mut self, why: &'static str) {
        *self.stats.rejected.entry(why).or_default() += 1;
    }

    pub fn deliver(&mut self, d: Delivery) {
        let me = d.to;
        if !self.nodes[me].alive || !self.nodes[me].gossip.first_seen(&d.env) {
            return;
        }
        let now = self.now;
        match self.nodes[me].verifier.open(&d.env, now) {
            Ok(message) => {
                if let Err(e) = message.validate(&d.env.from) {
                    self.reject(e.code());
                    return;
                }
                self.apply(me, &d.env, &message);
                self.fan_out(me, &d.env, d.via);
            }
            Err(e) => self.reject(e.code()),
        }
    }

    pub fn step(&mut self, dt: i64) {
        self.now += dt;
        let due: Vec<(i64, u64)> = self
            .queue
            .range(..=(self.now, u64::MAX))
            .map(|(k, _)| *k)
            .collect();
        for key in due {
            if let Some(d) = self.queue.remove(&key) {
                self.deliver(d);
            }
        }
        for i in 0..self.nodes.len() {
            self.tick_node(i);
        }
    }

    pub fn run(&mut self, ms: i64) {
        let end = self.now + ms;
        while self.now < end {
            self.step(50);
        }
    }

    pub fn run_until(&mut self, limit: i64, mut done: impl FnMut(&Sim) -> bool) -> bool {
        let end = self.now + limit;
        while self.now < end {
            self.step(50);
            if done(self) {
                return true;
            }
        }
        false
    }

    pub fn kill(&mut self, i: usize) {
        self.nodes[i].alive = false;
    }

    pub fn alive_count(&self) -> usize {
        self.nodes.iter().filter(|n| n.alive).count()
    }
}
