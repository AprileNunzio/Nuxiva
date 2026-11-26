use std::collections::{BTreeMap, BTreeSet};

use model_router::{Budget, Request, Router, Sensitivity, Task};

use crate::{
    Catalog, Device, FitError, Model, Need, Node, NodeClass, Quant, memory_mb, plan, profile,
};

fn model(id: &str, params_m: u32, understand: u16) -> Model {
    Model {
        id: id.into(),
        params_m,
        context_tokens: 32_768,
        kv_bytes_per_token: 65_536,
        quants: BTreeSet::from([Quant::F16, Quant::Q8, Quant::Q4, Quant::Q2]),
        base_quality_bps: BTreeMap::from([("understand".into(), understand)]),
        measured_bps: BTreeMap::new(),
    }
}

fn catalog() -> Catalog {
    Catalog::new(vec![
        model("qwen3-1.7b", 1_700, 7_000),
        model("qwen3-4b", 4_000, 8_000),
        model("qwen3-14b", 14_000, 9_000),
    ])
    .expect("catalog")
}

fn node(class: NodeClass, ram: u64, vram: u64) -> Node {
    Node {
        class,
        ram_free_mb: ram,
        vram_free_mb: vram,
        reserve_percent: 20,
        on_battery: false,
    }
}

fn need(min: u16) -> Need {
    Need {
        task: Task::Understand,
        context_tokens: 4_096,
        min_quality_bps: min,
    }
}

#[test]
fn memory_grows_with_bits_and_context() {
    let m = model("m", 4_000, 8_000);
    assert!(memory_mb(&m, Quant::F16, 4_096) > memory_mb(&m, Quant::Q4, 4_096));
    assert!(memory_mb(&m, Quant::Q4, 32_768) > memory_mb(&m, Quant::Q4, 4_096));
    let q4 = memory_mb(&m, Quant::Q4, 4_096);
    assert!((2_500..3_500).contains(&q4), "{q4}");
}

#[test]
fn a_big_gpu_server_gets_the_strongest_model() {
    let fit = plan(
        &node(NodeClass::Server, 64_000, 48_000),
        &catalog(),
        &need(6_000),
    )
    .expect("fit");
    assert_eq!(fit.model, "qwen3-14b");
    assert_eq!(fit.device, Device::Gpu);
    assert_eq!(fit.quant, Quant::F16);
}

#[test]
fn a_small_node_gets_a_quantized_model_that_fits() {
    let small = node(NodeClass::Node, 8_000, 0);
    let fit = plan(&small, &catalog(), &need(6_000)).expect("fit");
    assert_eq!(fit.device, Device::Cpu);
    assert!(fit.memory_mb <= small.usable_mb(Device::Cpu));
    assert_ne!(fit.quant, Quant::F16);
}

#[test]
fn satellites_never_load_large_models_and_shrink_on_battery() {
    let mut satellite = node(NodeClass::Satellite, 64_000, 0);
    let fit = plan(&satellite, &catalog(), &need(6_000)).expect("fit");
    assert_eq!(fit.model, "qwen3-4b");
    satellite.on_battery = true;
    let fit = plan(&satellite, &catalog(), &need(6_000)).expect("fit");
    assert_eq!(fit.model, "qwen3-1.7b");
}

#[test]
fn quality_floors_and_tiny_devices_yield_no_fit() {
    assert!(matches!(
        plan(&node(NodeClass::Node, 500, 0), &catalog(), &need(6_000)),
        Err(FitError::NoFit)
    ));
    assert!(matches!(
        plan(
            &node(NodeClass::Server, 64_000, 48_000),
            &catalog(),
            &need(9_500)
        ),
        Err(FitError::NoFit)
    ));
}

#[test]
fn lab_measurements_override_the_priors() {
    let mut c = catalog();
    let small = node(NodeClass::Node, 8_000, 0);
    let before = plan(&small, &c, &need(6_000)).expect("fit");
    c.record_measurement(&before.model, before.quant, 5_000)
        .expect("measure");
    let after = plan(&small, &c, &need(6_000)).expect("fit");
    assert_ne!(before.id, after.id);
    assert!(c.record_measurement("nope", Quant::Q4, 9_000).is_err());
    assert!(c.record_measurement("qwen3-4b", Quant::Q6, 9_000).is_err());
}

#[test]
fn malformed_catalogs_and_nodes_are_refused() {
    let mut bad = model("bad id", 1_000, 7_000);
    assert!(Catalog::new(vec![bad.clone()]).is_err());
    bad.id = "ok".into();
    bad.base_quality_bps.insert("dance".into(), 5_000);
    assert!(Catalog::new(vec![bad]).is_err());
    assert!(Catalog::new(vec![model("a", 1, 1), model("a", 1, 1)]).is_err());
    assert!(Catalog::from_json(br#"[{"id":"a","params_m":1}]"#).is_err());
    assert!(Catalog::from_json(&vec![b' '; 300 * 1024]).is_err());
    let mut n = node(NodeClass::Node, 8_000, 0);
    n.reserve_percent = 95;
    assert!(plan(&n, &catalog(), &need(6_000)).is_err());
}

#[test]
fn a_planned_model_registers_in_the_router_as_a_free_local_profile() {
    let c = catalog();
    let fit = plan(&node(NodeClass::Node, 16_000, 0), &c, &need(6_000)).expect("fit");
    let p = profile(&fit, &c, 900).expect("profile");
    assert_eq!(p.quality(Task::Understand), fit.expected_bps);
    let mut router = Router::new();
    router.register(p).expect("register");
    let decision = router
        .choose(
            &Request {
                task: Task::Understand,
                sensitivity: Sensitivity::Secret,
                input_tokens: 1_000,
                max_output: 500,
                min_quality_bps: 6_000,
                deadline_ms: None,
            },
            &mut Budget::new(0),
        )
        .expect("choose");
    assert_eq!(decision.model, fit.id);
    assert_eq!(decision.cost_micro, 0);
}
