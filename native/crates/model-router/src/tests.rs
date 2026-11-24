use std::collections::BTreeMap;

use crate::{
    Budget, Cache, Placement, Profile, Request, RouteError, Router, Sensitivity, Task, cache_key,
    compact, estimate_tokens,
};

fn profile(id: &str, placement: Placement, ctx: u32, price: u32, quality: u16) -> Profile {
    let rate = if placement == Placement::Local {
        0
    } else {
        price
    };
    Profile {
        id: id.into(),
        placement,
        context_tokens: ctx,
        micro_per_1k_in: rate,
        micro_per_1k_out: rate.saturating_mul(3),
        latency_ms: if placement == Placement::Local {
            900
        } else {
            400
        },
        quality_bps: BTreeMap::from([
            (Task::Understand, quality),
            (Task::Plan, quality),
            (Task::Summarize, quality),
        ]),
    }
}

fn router() -> Router {
    let mut router = Router::new();
    for p in [
        profile("ollama:small", Placement::Local, 8_000, 0, 7_000),
        profile("ollama:large", Placement::Local, 32_000, 0, 8_500),
        profile("cloud:fast", Placement::Cloud, 200_000, 100, 9_000),
        profile("cloud:best", Placement::Cloud, 200_000, 1_500, 9_800),
    ] {
        router.register(p).expect("register");
    }
    router
}

fn request(task: Task, sensitivity: Sensitivity, input: u32, quality: u16) -> Request {
    Request {
        task,
        sensitivity,
        input_tokens: input,
        max_output: 500,
        min_quality_bps: quality,
        deadline_ms: None,
    }
}

#[test]
fn easy_work_stays_on_the_free_local_model() {
    let mut budget = Budget::new(1_000_000);
    let d = router()
        .choose(
            &request(Task::Understand, Sensitivity::Public, 600, 6_500),
            &mut budget,
        )
        .expect("choose");
    assert_eq!(d.model, "ollama:small");
    assert_eq!(d.cost_micro, 0);
    assert_eq!(budget.spent(), 0);
}

#[test]
fn hard_work_escalates_to_the_cheapest_cloud_model_that_is_good_enough() {
    let mut budget = Budget::new(1_000_000);
    let d = router()
        .choose(
            &request(Task::Plan, Sensitivity::Public, 4_000, 9_000),
            &mut budget,
        )
        .expect("choose");
    assert_eq!(d.model, "cloud:fast");
    assert_eq!(d.fallbacks, vec!["cloud:best".to_owned()]);
    assert_eq!(budget.spent(), d.cost_micro);
    let d = router()
        .choose(
            &request(Task::Plan, Sensitivity::Public, 4_000, 9_500),
            &mut budget,
        )
        .expect("choose");
    assert_eq!(d.model, "cloud:best");
}

#[test]
fn long_inputs_skip_models_whose_context_is_too_small() {
    let mut budget = Budget::new(1_000_000);
    let d = router()
        .choose(
            &request(Task::Summarize, Sensitivity::Public, 20_000, 6_500),
            &mut budget,
        )
        .expect("choose");
    assert_eq!(d.model, "ollama:large");
    let d = router()
        .choose(
            &request(Task::Summarize, Sensitivity::Public, 100_000, 6_500),
            &mut budget,
        )
        .expect("choose");
    assert!(d.model.starts_with("cloud:"));
}

#[test]
fn secret_data_never_leaves_the_machine_even_if_it_means_failing() {
    let mut budget = Budget::new(1_000_000);
    let mut local_only = Router::new();
    local_only
        .register(profile("ollama:small", Placement::Local, 8_000, 0, 7_000))
        .expect("register");
    let r = router();
    let d = r
        .choose(
            &request(Task::Plan, Sensitivity::Secret, 600, 6_500),
            &mut budget,
        )
        .expect("choose");
    assert_eq!(d.model, "ollama:small");
    assert!(d.fallbacks.iter().all(|m| m.starts_with("ollama:")));
    assert_eq!(
        local_only.choose(
            &request(Task::Plan, Sensitivity::Secret, 600, 9_500),
            &mut budget
        ),
        Err(RouteError::NoModel)
    );
    assert_eq!(
        r.choose(
            &request(Task::Plan, Sensitivity::Secret, 600, 9_500),
            &mut budget
        ),
        Err(RouteError::NoModel)
    );
}

#[test]
fn the_budget_is_a_hard_ceiling() {
    let mut budget = Budget::new(10);
    assert_eq!(
        router().choose(
            &request(Task::Plan, Sensitivity::Public, 4_000, 9_000),
            &mut budget
        ),
        Err(RouteError::OverBudget)
    );
    assert_eq!(budget.spent(), 0);
}

#[test]
fn deadlines_exclude_slow_models() {
    let mut budget = Budget::new(1_000_000);
    let mut req = request(Task::Understand, Sensitivity::Public, 600, 6_500);
    req.deadline_ms = Some(500);
    let d = router().choose(&req, &mut budget).expect("choose");
    assert_eq!(d.model, "cloud:fast");
}

#[test]
fn invalid_profiles_are_rejected() {
    let mut router = Router::new();
    let mut bad = profile("x", Placement::Local, 8_000, 0, 7_000);
    bad.micro_per_1k_in = 5;
    assert!(router.register(bad).is_err());
    let mut bad = profile("bad id!", Placement::Local, 8_000, 0, 7_000);
    bad.id = "bad id!".into();
    assert!(router.register(bad).is_err());
    let mut bad = profile("q", Placement::Local, 8_000, 0, 7_000);
    bad.quality_bps.insert(Task::Plan, 10_001);
    assert!(router.register(bad).is_err());
}

#[test]
fn compaction_removes_duplicates_and_respects_the_token_budget() {
    let out = compact(
        &["  Hello   world ", "Hello world", "second   part", ""],
        100,
    )
    .expect("compact");
    assert_eq!(out, "Hello world\nsecond part");
    let long = "word ".repeat(400);
    let out = compact(&["short", &long, "tail"], 50).expect("compact");
    assert_eq!(out, "short");
    assert!(estimate_tokens(&out) <= 50);
    assert_eq!(compact(&[&long], 10), Err(RouteError::TooLarge));
}

#[test]
fn only_public_answers_are_cached_and_they_expire() {
    let mut cache = Cache::new(2, 60);
    let key = cache_key(Task::Summarize, "m", "  what is   rust ");
    assert_eq!(key, cache_key(Task::Summarize, "m", "what is rust"));
    assert_ne!(key, cache_key(Task::Plan, "m", "what is rust"));
    assert_ne!(key, cache_key(Task::Summarize, "other", "what is rust"));
    cache.put(key.clone(), "a language".into(), Sensitivity::Public, 100);
    assert_eq!(cache.get(&key, 120).as_deref(), Some("a language"));
    assert_eq!(cache.get(&key, 160), None);
    cache.put("p".into(), "x".into(), Sensitivity::Private, 0);
    cache.put("s".into(), "x".into(), Sensitivity::Secret, 0);
    assert!(cache.is_empty());
}

#[test]
fn the_cache_evicts_the_least_recently_used_entry() {
    let mut cache = Cache::new(2, 1_000);
    cache.put("a".into(), "1".into(), Sensitivity::Public, 0);
    cache.put("b".into(), "2".into(), Sensitivity::Public, 0);
    assert!(cache.get("a", 1).is_some());
    cache.put("c".into(), "3".into(), Sensitivity::Public, 0);
    assert_eq!(cache.len(), 2);
    assert!(cache.get("b", 1).is_none());
    assert!(cache.get("a", 1).is_some());
}
