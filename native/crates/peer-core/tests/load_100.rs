#![allow(clippy::pedantic)]
#![allow(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::panic,
    clippy::match_wildcard_for_single_variants,
    clippy::cast_possible_truncation,
    clippy::cast_precision_loss
)]

mod sim;

use nuxiva_peer_core::*;
use sim::Sim;

fn converge(sim: &mut Sim, nodes: usize) {
    sim.run(20_000);
    for size in sim.registry_sizes() {
        assert_eq!(size, nodes);
    }
}

fn workload(sim: &mut Sim, jobs: usize) -> Vec<u64> {
    let mut ids = Vec::new();
    for n in 0..jobs {
        let mut requester = 21 + sim.rng.below(79) as usize;
        while !sim.nodes[requester].alive {
            requester = 21 + sim.rng.below(79) as usize;
        }
        let kind = match n % 3 {
            0 => Kind::Render,
            1 => Kind::Compute,
            _ => Kind::Background,
        };
        let duration = 500 + sim.rng.below(2_500) as i64;
        ids.push(sim.submit_job(requester, kind, duration));
        sim.run(100);
    }
    ids
}

fn fairness(sim: &Sim) {
    let total: u64 = sim.nodes.iter().map(|n| n.sent).sum();
    let mean = total as f64 / sim.nodes.len() as f64;
    let max = sim.nodes.iter().map(|n| n.sent).max().expect("max") as f64;
    let server = sim.nodes[0].sent as f64;
    assert!(
        server / total as f64 <= 0.03,
        "server share {}",
        server / total as f64
    );
    assert!(max <= mean * 4.0, "max {max} mean {mean}");
}

#[test]
fn hundred_nodes_complete_all_jobs_without_server_bottleneck() {
    let mut sim = Sim::new(100, 0x00C0_FFEE);
    converge(&mut sim, 100);
    let jobs = workload(&mut sim, 300);
    let ok = sim.run_until(180_000, |s| jobs.iter().all(|j| s.stats.done.contains(j)));
    assert!(ok, "done {} of {}", sim.stats.done.len(), jobs.len());
    assert!(sim.stats.failed.is_empty());
    fairness(&sim);
    let duplicates = sim.stats.executed.values().filter(|v| v.len() > 1).count();
    assert!(duplicates * 10 <= jobs.len(), "duplicates {duplicates}");
    let background: Vec<u64> = jobs.iter().copied().filter(|j| j % 3 == 0).collect();
    let heavy_on_strong = background
        .iter()
        .filter(|j| {
            sim.stats
                .executed
                .get(j)
                .and_then(|v| v.first())
                .is_some_and(|n| sim.nodes[*n].caps.tier != Tier::Mobile)
        })
        .count();
    assert!(
        heavy_on_strong * 10 >= background.len() * 8,
        "{heavy_on_strong}/{}",
        background.len()
    );
    let renders: Vec<u64> = jobs.iter().copied().filter(|j| j % 3 == 1).collect();
    let local = renders
        .iter()
        .filter(|j| {
            sim.stats
                .executed
                .get(j)
                .and_then(|v| v.first())
                .is_some_and(|n| sim.ids[*n] == sim.nodes[*n].specs[j].requester)
        })
        .count();
    assert!(local * 10 >= renders.len() * 8, "{local}/{}", renders.len());
}

#[test]
fn thirty_nodes_including_server_die_midway_and_jobs_still_finish() {
    let mut sim = Sim::new(100, 0xBADC_0DE5);
    converge(&mut sim, 100);
    let first = workload(&mut sim, 120);
    sim.kill(0);
    let mut killed = 1;
    while killed < 30 {
        let victim = 1 + sim.rng.below(99) as usize;
        if sim.nodes[victim].alive {
            sim.kill(victim);
            killed += 1;
        }
    }
    let second = workload(&mut sim, 120);
    let all: Vec<u64> = first.into_iter().chain(second).collect();
    let survivors: Vec<u64> = all
        .into_iter()
        .filter(|j| {
            sim.nodes
                .iter()
                .any(|n| n.alive && n.outstanding.contains_key(j))
                || sim.stats.done.contains(j)
        })
        .collect();
    let ok = sim.run_until(240_000, |s| {
        survivors.iter().all(|j| {
            s.stats.done.contains(j)
                && !s
                    .nodes
                    .iter()
                    .any(|n| n.alive && n.outstanding.contains_key(j))
        })
    });
    assert!(
        ok,
        "pending {}",
        survivors
            .iter()
            .filter(|j| !sim.stats.done.contains(j))
            .count()
    );
    assert_eq!(sim.alive_count(), 70);
    assert!(survivors.len() >= 100, "survivors {}", survivors.len());
}

#[test]
fn forged_replayed_and_unenrolled_traffic_never_executes() {
    let mut sim = Sim::new(100, 0x5EC0_0001);
    converge(&mut sim, 100);
    let intruder = PeerKey::generate().expect("key");
    let legit = workload(&mut sim, 30);
    let rogue_spec = JobSpec {
        id: 900_001,
        kind: Kind::Compute,
        needs: job::Needs {
            cpu_cores: 1,
            ram_mb: 64,
            gpu_vram_mb: 0,
            display: false,
        },
        priority: 9,
        max_attempts: 3,
        lease_ms: 4_000,
        deadline_ms: 0,
        min_battery_pct: 0,
        requester: intruder.id().to_owned(),
        affinity: None,
    };
    let rogue = intruder
        .seal(1, sim.now, 6, &Message::Submit { spec: rogue_spec })
        .expect("seal");
    for to in 0..100 {
        sim.enqueue(to, None, rogue.clone());
    }
    let captured = sim.tap.last().expect("tap").clone();
    for to in 0..100 {
        sim.enqueue(to, None, captured.clone());
    }
    let mut tampered = captured.clone();
    tampered.payload = serde_json::to_string(&Message::Progress { job: 7 }).expect("json");
    for to in 0..100 {
        sim.enqueue(to, None, tampered.clone());
    }
    let liar = 50usize;
    let liar_assign = sim.nodes[liar].seal(
        sim.now,
        6,
        &Message::Assign {
            job: legit[0],
            node: sim.ids[60].clone(),
            lease_until: sim.now + 4_000,
        },
    );
    for to in 0..100 {
        sim.enqueue(to, None, liar_assign.clone());
    }
    let ok = sim.run_until(120_000, |s| legit.iter().all(|j| s.stats.done.contains(j)));
    assert!(ok);
    assert!(!sim.stats.executed.contains_key(&900_001));
    assert!(
        sim.stats
            .rejected
            .get("peer.error.untrusted")
            .copied()
            .unwrap_or(0)
            >= 100
    );
    assert!(
        sim.stats
            .rejected
            .get("peer.error.signature")
            .copied()
            .unwrap_or(0)
            >= 1
    );
}
