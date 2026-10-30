use crate::{HostProfile, Limit, Mode, ModelProfile, Settings, capacity};

const PI: HostProfile = HostProfile {
    cpu_cores: 4,
    ram_mb: 8_192,
    vram_mb: 0,
};

const WORKSTATION: HostProfile = HostProfile {
    cpu_cores: 16,
    ram_mb: 65_536,
    vram_mb: 24_576,
};

#[test]
fn small_board_with_local_model_runs_one_agent() {
    let result = capacity(
        &PI,
        &ModelProfile::Local { size_mb: 4_700 },
        &Settings::default(),
    );
    assert_eq!(result.parallel_agents, 1);
}

#[test]
fn gpu_workstation_is_bound_by_vram() {
    let result = capacity(
        &WORKSTATION,
        &ModelProfile::Local { size_mb: 8_000 },
        &Settings::default(),
    );
    assert_eq!(result.limit, Limit::GpuMemory);
    assert_eq!(result.parallel_agents, 16);
}

#[test]
fn model_larger_than_vram_falls_back_to_ram_and_cpu() {
    let result = capacity(
        &WORKSTATION,
        &ModelProfile::Local { size_mb: 40_000 },
        &Settings::default(),
    );
    assert_eq!(result.limit, Limit::Memory);
    assert_eq!(result.parallel_agents, 4);
}

#[test]
fn cloud_is_bound_by_rate_limit() {
    let result = capacity(
        &WORKSTATION,
        &ModelProfile::Cloud {
            requests_per_minute: 30,
        },
        &Settings::default(),
    );
    assert_eq!(
        (result.parallel_agents, result.limit),
        (5, Limit::RateLimit)
    );
}

#[test]
fn manual_mode_respects_the_cap() {
    let settings = Settings {
        mode: Mode::Manual,
        manual_parallel: 40,
        max_parallel: 8,
        reserve_ram_mb: 0,
    };
    let result = capacity(&PI, &ModelProfile::Local { size_mb: 1 }, &settings);
    assert_eq!((result.parallel_agents, result.limit), (8, Limit::Manual));
}

#[test]
fn settings_validation() {
    assert!(Settings::default().validate().is_ok());
    let zero = Settings {
        manual_parallel: 0,
        ..Settings::default()
    };
    assert!(zero.validate().is_err());
    let huge = Settings {
        max_parallel: 65,
        ..Settings::default()
    };
    assert!(huge.validate().is_err());
}

#[test]
fn never_returns_zero() {
    let empty = HostProfile {
        cpu_cores: 0,
        ram_mb: 0,
        vram_mb: 0,
    };
    let result = capacity(
        &empty,
        &ModelProfile::Cloud {
            requests_per_minute: 0,
        },
        &Settings::default(),
    );
    assert_eq!(result.parallel_agents, 1);
}
