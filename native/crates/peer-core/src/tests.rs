use crate::capability::Roles;
use crate::job::Needs;
use crate::*;

fn caps(tier: Tier, cores: u16, score: u32, ram: u32, battery: Option<u8>) -> Capabilities {
    Capabilities {
        tier,
        roles: Roles {
            display: true,
            compute: true,
            coordinate: true,
        },
        cpu_cores: cores,
        cpu_score: score,
        ram_mb: ram,
        gpu_vram_mb: 0,
        gpu_score: 0,
        battery_pct: battery,
        charging: false,
        uplink_kbps: 100_000,
        rtt_ms: 5,
    }
}

fn spec(id: u64, requester: &str, kind: Kind) -> JobSpec {
    JobSpec {
        id,
        kind,
        needs: Needs {
            cpu_cores: 4,
            ram_mb: 2048,
            gpu_vram_mb: 0,
            display: false,
        },
        priority: 5,
        max_attempts: 3,
        lease_ms: 5_000,
        deadline_ms: 0,
        min_battery_pct: 0,
        requester: requester.to_owned(),
        affinity: None,
    }
}

fn keys(n: usize) -> Vec<PeerKey> {
    (0..n)
        .map(|i| {
            let mut seed = [7u8; 32];
            seed[0] = u8::try_from(i).expect("small");
            PeerKey::from_seed(&seed).expect("key")
        })
        .collect()
}

#[test]
fn envelope_roundtrip_and_tamper() {
    let k = keys(2);
    let mut trust = TrustBook::new();
    trust.enroll(k[0].id()).expect("enroll");
    let mut verifier = Verifier::new(trust);
    let env = k[0].seal(1, 1_000, 6, &Message::Leave).expect("seal");
    assert_eq!(verifier.open(&env, 1_000).expect("open"), Message::Leave);
    assert_eq!(verifier.open(&env, 1_000), Err(PeerError::Replay));
    let mut forged = k[0].seal(2, 1_000, 6, &Message::Leave).expect("seal");
    forged.payload = serde_json::to_string(&Message::Progress { job: 1 }).expect("json");
    assert_eq!(verifier.open(&forged, 1_000), Err(PeerError::Signature));
    let stranger = k[1].seal(1, 1_000, 6, &Message::Leave).expect("seal");
    assert_eq!(verifier.open(&stranger, 1_000), Err(PeerError::Untrusted));
    let old = k[0].seal(3, 1_000, 6, &Message::Leave).expect("seal");
    assert_eq!(verifier.open(&old, 1_000 + 120_000), Err(PeerError::Clock));
}

#[test]
fn replay_window_accepts_reorder_once() {
    let k = keys(1);
    let mut trust = TrustBook::new();
    trust.enroll(k[0].id()).expect("enroll");
    let mut verifier = Verifier::new(trust);
    let a = k[0].seal(10, 0, 1, &Message::Leave).expect("seal");
    let b = k[0].seal(9, 0, 1, &Message::Leave).expect("seal");
    let far = k[0].seal(200, 0, 1, &Message::Leave).expect("seal");
    let stale = k[0].seal(8, 0, 1, &Message::Leave).expect("seal");
    assert!(verifier.open(&a, 0).is_ok());
    assert!(verifier.open(&b, 0).is_ok());
    assert_eq!(verifier.open(&b, 0), Err(PeerError::Replay));
    assert!(verifier.open(&far, 0).is_ok());
    assert_eq!(verifier.open(&stale, 0), Err(PeerError::Replay));
}

#[test]
fn registry_ignores_stale_and_expires() {
    let k = keys(1);
    let mut reg = Registry::new(Liveness::default());
    let c = caps(Tier::Desktop, 8, 5000, 16_000, None);
    assert!(reg.announce(k[0].id(), 2, c, 0).expect("a"));
    assert!(!reg.announce(k[0].id(), 1, c, 0).expect("a"));
    assert!(reg.is_alive(k[0].id()));
    reg.sweep(7_000);
    assert_eq!(reg.get(k[0].id()).expect("e").status, Status::Suspect);
    reg.sweep(16_000);
    assert_eq!(reg.get(k[0].id()).expect("e").status, Status::Dead);
    reg.touch(k[0].id(), 17_000);
    assert!(reg.is_alive(k[0].id()));
}

#[test]
fn rejects_invalid_capabilities() {
    let k = keys(1);
    let mut reg = Registry::new(Liveness::default());
    let mut c = caps(Tier::Mobile, 8, 100, 4000, Some(50));
    c.battery_pct = Some(150);
    assert_eq!(reg.announce(k[0].id(), 1, c, 0), Err(PeerError::Field));
    assert_eq!(
        reg.announce("zz", 1, caps(Tier::Mobile, 1, 1, 1, None), 0),
        Err(PeerError::Field)
    );
}

#[test]
fn heavy_job_goes_to_strongest_not_to_low_battery_phone() {
    let k = keys(3);
    let mut reg = Registry::new(Liveness::default());
    reg.announce(k[0].id(), 1, caps(Tier::Server, 8, 9000, 32_000, None), 0)
        .expect("a");
    reg.announce(k[1].id(), 1, caps(Tier::Mobile, 8, 3000, 8000, Some(12)), 0)
        .expect("a");
    reg.announce(k[2].id(), 1, caps(Tier::Mobile, 8, 3000, 8000, Some(90)), 0)
        .expect("a");
    let mut sched = Scheduler::new();
    sched
        .submit(spec(1, k[2].id(), Kind::Background))
        .expect("s");
    let out = sched.tick(&reg, 0);
    match &out[0] {
        Decision::Assign { node, degraded, .. } => {
            assert_eq!(node, k[0].id());
            assert!(!degraded);
        }
        other => panic!("{other:?}"),
    }
}

#[test]
fn render_prefers_affinity_display_node() {
    let k = keys(2);
    let mut reg = Registry::new(Liveness::default());
    let mut phone = caps(Tier::Mobile, 8, 3000, 8000, Some(80));
    phone.gpu_vram_mb = 2048;
    phone.gpu_score = 4000;
    reg.announce(k[0].id(), 1, caps(Tier::Server, 8, 9000, 32_000, None), 0)
        .expect("a");
    reg.announce(k[1].id(), 1, phone, 0).expect("a");
    let mut job = spec(2, k[1].id(), Kind::Render);
    job.needs.display = true;
    job.needs.cpu_cores = 1;
    job.needs.gpu_vram_mb = 512;
    job.affinity = Some(k[1].id().to_owned());
    let mut sched = Scheduler::new();
    sched.submit(job).expect("s");
    match &sched.tick(&reg, 0)[0] {
        Decision::Assign { node, .. } => assert_eq!(node, k[1].id()),
        other => panic!("{other:?}"),
    }
}

#[test]
fn failover_on_dead_node_then_fails_after_attempts() {
    let k = keys(3);
    let mut reg = Registry::new(Liveness::default());
    for key in &k {
        reg.announce(key.id(), 1, caps(Tier::Desktop, 8, 5000, 16_000, None), 0)
            .expect("a");
    }
    let mut sched = Scheduler::new();
    sched.submit(spec(3, k[0].id(), Kind::Compute)).expect("s");
    let first = match &sched.tick(&reg, 0)[0] {
        Decision::Assign { node, .. } => node.clone(),
        other => panic!("{other:?}"),
    };
    reg.leave(&first);
    let second = match &sched.tick(&reg, 100)[0] {
        Decision::Assign { node, attempt, .. } => {
            assert_eq!(*attempt, 2);
            node.clone()
        }
        other => panic!("{other:?}"),
    };
    assert_ne!(first, second);
    reg.leave(&second);
    let third = match &sched.tick(&reg, 200)[0] {
        Decision::Assign { node, .. } => node.clone(),
        other => panic!("{other:?}"),
    };
    reg.leave(&third);
    let last = sched.tick(&reg, 300);
    assert_eq!(
        last,
        vec![Decision::Failed {
            job: 3,
            reason: Reason::Attempts
        }]
    );
}

#[test]
fn degraded_fallback_when_strict_does_not_fit() {
    let k = keys(1);
    let mut reg = Registry::new(Liveness::default());
    reg.announce(k[0].id(), 1, caps(Tier::Desktop, 2, 2000, 3000, None), 0)
        .expect("a");
    let mut sched = Scheduler::new();
    sched.submit(spec(4, k[0].id(), Kind::Compute)).expect("s");
    match &sched.tick(&reg, 0)[0] {
        Decision::Assign { degraded, .. } => assert!(degraded),
        other => panic!("{other:?}"),
    }
}

#[test]
fn lease_expiry_reassigns_and_renew_keeps() {
    let k = keys(2);
    let mut reg = Registry::new(Liveness {
        suspect_after_ms: 60_000,
        dead_after_ms: 120_000,
    });
    for key in &k {
        reg.announce(key.id(), 1, caps(Tier::Desktop, 8, 5000, 16_000, None), 0)
            .expect("a");
    }
    let mut sched = Scheduler::new();
    sched.submit(spec(5, k[0].id(), Kind::Compute)).expect("s");
    let node = match &sched.tick(&reg, 0)[0] {
        Decision::Assign { node, .. } => node.clone(),
        other => panic!("{other:?}"),
    };
    sched.renew(5, &node, 4_000).expect("renew");
    assert!(sched.tick(&reg, 8_000).is_empty());
    let out = sched.tick(&reg, 9_500);
    assert!(matches!(&out[0], Decision::Assign { node: n, .. } if *n != node));
}

#[test]
fn duplicate_submit_is_idempotent_and_wrong_node_cannot_complete() {
    let k = keys(2);
    let mut reg = Registry::new(Liveness::default());
    reg.announce(k[0].id(), 1, caps(Tier::Desktop, 8, 5000, 16_000, None), 0)
        .expect("a");
    let mut sched = Scheduler::new();
    assert!(sched.submit(spec(6, k[0].id(), Kind::Compute)).expect("s"));
    assert!(!sched.submit(spec(6, k[0].id(), Kind::Compute)).expect("s"));
    sched.tick(&reg, 0);
    assert_eq!(sched.complete(6, k[1].id()), Err(PeerError::State));
    sched.complete(6, k[0].id()).expect("done");
    assert_eq!(sched.phase(6), Some(&Phase::Done));
}

#[test]
fn election_is_deterministic_and_skips_dead() {
    let k = keys(5);
    let mut reg = Registry::new(Liveness::default());
    for key in &k {
        reg.announce(key.id(), 1, caps(Tier::Desktop, 4, 1000, 4000, None), 0)
            .expect("a");
    }
    let first = election::coordinator_for(42, &reg).expect("c");
    assert_eq!(Some(first.clone()), election::coordinator_for(42, &reg));
    reg.leave(&first);
    assert_ne!(Some(first), election::coordinator_for(42, &reg));
}

#[test]
fn gossip_dedupes_and_respects_ttl() {
    let k = keys(8);
    let ids: Vec<String> = k.iter().map(|x| x.id().to_owned()).collect();
    let mut g = Gossip::new(3);
    let env = k[0].seal(1, 0, 2, &Message::Leave).expect("seal");
    assert!(g.first_seen(&env));
    assert!(!g.first_seen(&env));
    let t = g.targets(&ids[1], &env, Some(&ids[2]), &ids);
    assert_eq!(t.len(), 3);
    assert!(!t.contains(&ids[1]) && !t.contains(&ids[2]) && !t.contains(&ids[0]));
    assert!(g.targets(&ids[1], &env.hop().hop(), None, &ids).is_empty());
}
