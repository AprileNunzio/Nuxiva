use crate::{
    AgentSpec, EntitySpec, EventSpec, ForesightError, Leaning, MAX_RUNS, RelationSpec,
    ScenarioSpec, Traits, World, WorldState, ensemble,
};

fn traits(stance: f64) -> Traits {
    Traits {
        stance,
        openness: 0.6,
        activity: 0.7,
        influence: 0.5,
        stubbornness: 0.2,
        forum: 0.3,
    }
}

fn agent(i: usize, stance: f64, entity: &str) -> AgentSpec {
    AgentSpec {
        key: format!("a{i}"),
        name: format!("Agent {i}"),
        role: if i % 2 == 0 { "citizen" } else { "expert" }.to_owned(),
        entity: Some(entity.to_owned()),
        traits: traits(stance),
        follows: Vec::new(),
    }
}

fn scenario(n: usize, rounds: u16) -> ScenarioSpec {
    let agents = (0..n)
        .map(|i| {
            let side = if i % 2 == 0 { "north" } else { "south" };
            let stance = if i % 3 == 0 { 0.4 } else { -0.2 };
            agent(i, stance, side)
        })
        .collect();
    ScenarioSpec {
        title: "Town square".to_owned(),
        question: "Will the new park be approved?".to_owned(),
        seed: 7,
        rounds,
        entities: vec![
            EntitySpec {
                key: "north".to_owned(),
                name: "North district".to_owned(),
                kind: "place".to_owned(),
            },
            EntitySpec {
                key: "south".to_owned(),
                name: "South district".to_owned(),
                kind: "place".to_owned(),
            },
        ],
        relations: vec![RelationSpec {
            from: "north".to_owned(),
            to: "south".to_owned(),
            kind: "rival".to_owned(),
            weight: -0.4,
        }],
        agents,
        events: Vec::new(),
    }
}

#[test]
fn deterministic_for_same_seed() -> Result<(), ForesightError> {
    let mut a = World::new(scenario(60, 30))?;
    let mut b = World::new(scenario(60, 30))?;
    a.advance(30);
    b.advance(30);
    assert_eq!(a.state(), b.state());
    assert!(a.finished());
    assert_eq!(a.state().history.len(), 31);
    Ok(())
}

#[test]
fn stances_stay_bounded_and_activity_happens() -> Result<(), ForesightError> {
    let mut world = World::new(scenario(120, 40))?;
    world.advance(40);
    assert!(
        world
            .state()
            .agents
            .iter()
            .all(|a| (-1.0..=1.0).contains(&a.stance))
    );
    let posts: u32 = world.state().history.iter().map(|s| s.posts).sum();
    assert!(posts > 0);
    assert!(
        world
            .state()
            .agents
            .iter()
            .all(|a| a.memory.len() <= crate::agent::MEMORY)
    );
    Ok(())
}

#[test]
fn strong_event_moves_opinion() -> Result<(), ForesightError> {
    let mut base = World::new(scenario(100, 20))?;
    base.advance(20);
    let mut spec = scenario(100, 20);
    for round in [2, 5, 8, 11] {
        spec.events.push(EventSpec {
            round,
            title: "Funding announced".to_owned(),
            shift: 1.0,
            reach: 0.9,
            target: None,
        });
    }
    let mut pushed = World::new(spec)?;
    pushed.advance(20);
    let a = base.latest().map_or(0.0, |s| s.mean);
    let b = pushed.latest().map_or(0.0, |s| s.mean);
    assert!(b > a, "event should raise support: {a} -> {b}");
    let report = pushed.report();
    assert_eq!(report.events.len(), 4);
    assert!(report.events.iter().all(|e| e.reached > 0));
    Ok(())
}

#[test]
fn inject_only_into_the_future() -> Result<(), ForesightError> {
    let mut world = World::new(scenario(20, 10))?;
    world.advance(5);
    let past = EventSpec {
        round: 3,
        title: "Late news".to_owned(),
        shift: 0.5,
        reach: 0.5,
        target: None,
    };
    assert!(world.inject(past).is_err());
    let future = EventSpec {
        round: 7,
        title: "Fresh news".to_owned(),
        shift: -0.5,
        reach: 0.5,
        target: Some("south".to_owned()),
    };
    world.inject(future)?;
    let unknown = EventSpec {
        round: 8,
        title: "Ghost".to_owned(),
        shift: 0.1,
        reach: 0.1,
        target: Some("nowhere".to_owned()),
    };
    assert_eq!(
        world.inject(unknown),
        Err(ForesightError::Unknown("event target"))
    );
    world.advance(10);
    assert!(world.finished());
    assert!(
        world
            .inject(EventSpec {
                round: 10,
                title: "Too late".to_owned(),
                shift: 0.1,
                reach: 0.1,
                target: None,
            })
            .is_err()
    );
    Ok(())
}

#[test]
fn snapshot_round_trip_and_tamper_detection() -> Result<(), Box<dyn std::error::Error>> {
    let mut world = World::new(scenario(30, 12))?;
    world.advance(6);
    let bytes = serde_json::to_vec(world.state())?;
    let state: WorldState = serde_json::from_slice(&bytes)?;
    let mut restored = World::restore(state)?;
    world.advance(6);
    restored.advance(6);
    assert_eq!(world.state(), restored.state());
    let mut bad: WorldState = serde_json::from_slice(&bytes)?;
    bad.round = 11;
    assert_eq!(World::restore(bad).err(), Some(ForesightError::Corrupt));
    let mut bad: WorldState = serde_json::from_slice(&bytes)?;
    if let Some(a) = bad.agents.first_mut() {
        a.follows.insert(999);
    }
    assert_eq!(World::restore(bad).err(), Some(ForesightError::Corrupt));
    Ok(())
}

#[test]
fn validation_rejects_bad_input() {
    let mut spec = scenario(4, 5);
    spec.title = "bad\u{202E}title".to_owned();
    assert!(World::new(spec).is_err());
    let mut spec = scenario(4, 5);
    if let Some(a) = spec.agents.get_mut(0) {
        a.traits.openness = f64::NAN;
    }
    assert!(World::new(spec).is_err());
    let mut spec = scenario(4, 5);
    if let Some(a) = spec.agents.get_mut(1) {
        a.key = "a0".to_owned();
    }
    assert_eq!(
        World::new(spec).err(),
        Some(ForesightError::Duplicate("agents"))
    );
    let mut spec = scenario(4, 5);
    if let Some(a) = spec.agents.get_mut(0) {
        a.follows.push("a0".to_owned());
    }
    assert!(World::new(spec).is_err());
    let mut spec = scenario(4, 5);
    spec.rounds = 0;
    assert!(World::new(spec).is_err());
    let mut spec = scenario(4, 5);
    if let Some(a) = spec.agents.get_mut(0) {
        a.key = "../etc".to_owned();
    }
    assert!(World::new(spec).is_err());
    assert_eq!(
        World::new(scenario(2_000, 720)).err(),
        Some(ForesightError::Limit("work"))
    );
}

#[test]
fn report_and_agent_view() -> Result<(), ForesightError> {
    let mut world = World::new(scenario(50, 15))?;
    world.advance(15);
    let report = world.report();
    assert_eq!(report.trajectory.len(), 16);
    assert_eq!(report.histogram.iter().sum::<u32>(), 50);
    assert_eq!(report.roles.len(), 2);
    assert_eq!(report.entities.len(), 2);
    assert!(report.influencers.len() <= 10);
    let view = world.agent("a3")?;
    assert_eq!(view.name, "Agent 3");
    assert_ne!(view.memory, [] as [crate::view::MemoryView; 0]);
    assert_eq!(world.agent("zz").err(), Some(ForesightError::AgentNotFound));
    Ok(())
}

#[test]
fn ensemble_counts_every_run() -> Result<(), ForesightError> {
    let spec = scenario(40, 10);
    let result = ensemble(&spec, 8)?;
    assert_eq!(
        result.support + result.oppose + result.divided + result.undecided,
        8
    );
    assert!(result.low <= result.median && result.median <= result.high);
    assert!(ensemble(&spec, MAX_RUNS + 1).is_err());
    assert!(ensemble(&spec, 0).is_err());
    Ok(())
}

#[test]
fn unanimous_crowd_leans_support() -> Result<(), ForesightError> {
    let mut spec = scenario(30, 10);
    for a in &mut spec.agents {
        a.traits.stance = 0.8;
    }
    let mut world = World::new(spec)?;
    world.advance(10);
    assert_eq!(world.report().outcome.leaning, Leaning::Support);
    Ok(())
}
