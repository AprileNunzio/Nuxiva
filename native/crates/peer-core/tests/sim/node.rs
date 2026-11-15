#![allow(clippy::pedantic)]
#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::match_wildcard_for_single_variants,
    clippy::cast_possible_truncation
)]

use super::Sim;
use nuxiva_peer_core::capability::Roles;
use nuxiva_peer_core::election;
use nuxiva_peer_core::job::Needs;
use nuxiva_peer_core::*;
use std::collections::BTreeMap;

pub struct SimNode {
    pub key: PeerKey,
    pub verifier: Verifier,
    pub registry: Registry,
    pub gossip: Gossip,
    pub scheduler: Scheduler,
    pub caps: Capabilities,
    pub alive: bool,
    pub seq: u64,
    pub sent: u64,
    pub received: u64,
    pub specs: BTreeMap<u64, JobSpec>,
    pub running: BTreeMap<u64, (i64, i64)>,
    pub outstanding: BTreeMap<u64, i64>,
    pub next_heartbeat: i64,
    pub next_announce: i64,
    pub next_sweep: i64,
    pub next_tick: i64,
    pub started: bool,
    pub finished: std::collections::BTreeSet<u64>,
}

impl SimNode {
    pub fn new(key: PeerKey, trust: TrustBook, caps: Capabilities, offset: i64) -> Self {
        Self {
            key,
            verifier: Verifier::new(trust),
            registry: Registry::new(Liveness {
                suspect_after_ms: 9_000,
                dead_after_ms: 20_000,
            }),
            gossip: Gossip::new(5),
            scheduler: Scheduler::new(),
            caps,
            alive: true,
            seq: 0,
            sent: 0,
            received: 0,
            specs: BTreeMap::new(),
            running: BTreeMap::new(),
            outstanding: BTreeMap::new(),
            next_heartbeat: offset,
            next_announce: offset,
            next_sweep: 1_000,
            next_tick: 250,
            started: false,
            finished: std::collections::BTreeSet::new(),
        }
    }

    pub fn seal(&mut self, now: i64, ttl: u8, message: &Message) -> Envelope {
        self.seq += 1;
        self.key.seal(self.seq, now, ttl, message).expect("seal")
    }

    pub fn load(&self) -> Load {
        let running = u16::try_from(self.running.len()).unwrap_or(u16::MAX);
        Load {
            cpu_pct: u8::try_from((self.running.len() * 25).min(100)).unwrap_or(100),
            ram_free_mb: self.caps.ram_mb.saturating_sub(u32::from(running) * 1024),
            jobs_running: running,
            battery_pct: self.caps.battery_pct,
            charging: self.caps.charging,
        }
    }
}

const TTL: u8 = 6;

impl Sim {
    pub fn submit_job(&mut self, requester: usize, kind: Kind, duration: i64) -> u64 {
        let id = self.next_job;
        self.next_job += 1;
        let needs = match kind {
            Kind::Render => Needs {
                cpu_cores: 1,
                ram_mb: 512,
                gpu_vram_mb: 512,
                display: true,
            },
            Kind::Compute => Needs {
                cpu_cores: 2,
                ram_mb: 2048,
                gpu_vram_mb: 0,
                display: false,
            },
            Kind::Background => Needs {
                cpu_cores: 4,
                ram_mb: 4096,
                gpu_vram_mb: 0,
                display: false,
            },
        };
        let spec = JobSpec {
            id,
            kind,
            needs,
            priority: if kind == Kind::Render { 9 } else { 4 },
            max_attempts: 6,
            lease_ms: 4_000,
            deadline_ms: 0,
            min_battery_pct: 0,
            requester: self.ids[requester].clone(),
            affinity: (kind == Kind::Render).then(|| self.ids[requester].clone()),
        };
        self.stats.durations.insert(id, duration);
        self.nodes[requester].outstanding.insert(id, self.now);
        self.emit(requester, &Message::Submit { spec }, TTL);
        id
    }

    pub fn apply(&mut self, me: usize, env: &Envelope, message: &Message) {
        let now = self.now;
        let my_id = self.ids[me].clone();
        self.nodes[me].registry.touch(&env.from, now);
        match message {
            Message::Announce { caps } => {
                let _ = self.nodes[me]
                    .registry
                    .announce(&env.from, env.seq, *caps, now);
            }
            Message::Heartbeat { load } => {
                let _ = self.nodes[me]
                    .registry
                    .heartbeat(&env.from, env.seq, *load, now);
            }
            Message::Leave => self.nodes[me].registry.leave(&env.from),
            Message::Submit { spec } => {
                if self.nodes[me].finished.contains(&spec.id) {
                    self.emit(
                        me,
                        &Message::Result {
                            job: spec.id,
                            ok: true,
                        },
                        TTL,
                    );
                    return;
                }
                self.nodes[me].specs.insert(spec.id, spec.clone());
                let owner = election::coordinator_for(spec.id, &self.nodes[me].registry);
                if owner.as_deref() == Some(my_id.as_str()) {
                    let _ = self.nodes[me].scheduler.submit(spec.clone());
                }
            }
            Message::Assign { job, node, .. } => {
                let known = self.nodes[me].specs.contains_key(job);
                let legit = election::authorized(*job, &env.from, &self.nodes[me].registry, 3);
                if *node != my_id || self.nodes[me].running.contains_key(job) {
                    return;
                }
                if !known || !legit {
                    self.reject("peer.sim.assign_refused");
                    return;
                }
                let duration = self.stats.durations.get(job).copied().unwrap_or(1_000);
                let lease = i64::from(self.nodes[me].specs[job].lease_ms);
                self.nodes[me]
                    .running
                    .insert(*job, (now + duration, now + lease / 3));
                self.stats.executed.entry(*job).or_default().push(me);
            }
            Message::Progress { job } => {
                let _ = self.nodes[me].scheduler.renew(*job, &env.from, now);
            }
            Message::Result { job, ok } => {
                self.nodes[me].outstanding.remove(job);
                if *ok {
                    let _ = self.nodes[me].scheduler.complete(*job, &env.from);
                } else {
                    let _ = self.nodes[me].scheduler.fail(*job, &env.from);
                }
            }
        }
    }

    pub fn tick_node(&mut self, i: usize) {
        if !self.nodes[i].alive {
            return;
        }
        let now = self.now;
        if !self.nodes[i].started {
            self.nodes[i].started = true;
            let caps = self.nodes[i].caps;
            self.emit(i, &Message::Announce { caps }, TTL);
        }
        if now >= self.nodes[i].next_heartbeat {
            self.nodes[i].next_heartbeat = now + 5_000;
            let load = self.nodes[i].load();
            self.emit(i, &Message::Heartbeat { load }, TTL);
        }
        if now >= self.nodes[i].next_announce {
            self.nodes[i].next_announce = now + 12_000;
            let caps = self.nodes[i].caps;
            self.emit(i, &Message::Announce { caps }, TTL);
        }
        if now >= self.nodes[i].next_sweep {
            self.nodes[i].next_sweep = now + 1_000;
            self.nodes[i].registry.sweep(now);
        }
        self.tick_running(i);
        self.tick_resubmit(i);
        if now >= self.nodes[i].next_tick {
            self.nodes[i].next_tick = now + 250;
            let node = &mut self.nodes[i];
            let decisions = if node.scheduler.is_idle() {
                Vec::new()
            } else {
                node.scheduler.tick(&node.registry, now)
            };
            for d in decisions {
                match d {
                    Decision::Assign {
                        job,
                        node,
                        lease_until,
                        ..
                    } => {
                        self.emit(
                            i,
                            &Message::Assign {
                                job,
                                node,
                                lease_until,
                            },
                            TTL,
                        );
                    }
                    Decision::Failed { job, .. } => {
                        self.stats.failed.insert(job);
                    }
                }
            }
        }
    }

    fn tick_running(&mut self, i: usize) {
        let now = self.now;
        let jobs: Vec<(u64, (i64, i64))> = self.nodes[i]
            .running
            .iter()
            .map(|(k, v)| (*k, *v))
            .collect();
        for (job, (finish, progress)) in jobs {
            if now >= finish {
                self.nodes[i].running.remove(&job);
                self.nodes[i].finished.insert(job);
                self.stats.done.insert(job);
                self.emit(i, &Message::Result { job, ok: true }, TTL);
            } else if now >= progress {
                let lease = i64::from(self.nodes[i].specs.get(&job).map_or(4_000, |s| s.lease_ms));
                if let Some(slot) = self.nodes[i].running.get_mut(&job) {
                    slot.1 = now + lease / 3;
                }
                self.emit(i, &Message::Progress { job }, TTL);
            }
        }
    }

    fn tick_resubmit(&mut self, i: usize) {
        let now = self.now;
        let stale: Vec<u64> = self.nodes[i]
            .outstanding
            .iter()
            .filter(|(_, at)| now - **at >= 10_000)
            .map(|(id, _)| *id)
            .collect();
        for job in stale {
            if let Some(spec) = self.nodes[i].specs.get(&job).cloned() {
                self.nodes[i].outstanding.insert(job, now);
                self.emit(i, &Message::Submit { spec }, TTL);
            }
        }
    }

    pub fn registry_sizes(&self) -> Vec<usize> {
        self.nodes
            .iter()
            .filter(|n| n.alive)
            .map(|n| n.registry.len())
            .collect()
    }

    pub fn role_of(&self, i: usize) -> Roles {
        self.nodes[i].caps.roles
    }
}
