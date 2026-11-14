use crate::{McpError, Settings};

#[test]
fn resilience_settings_are_validated() {
    for broken in [
        Settings {
            foreground_budget_ms: 0,
            ..Settings::default()
        },
        Settings {
            max_jobs: 0,
            ..Settings::default()
        },
        Settings {
            error_queue: 0,
            ..Settings::default()
        },
        Settings {
            critic_threshold: 0,
            ..Settings::default()
        },
        Settings {
            critic_window_ms: 0,
            ..Settings::default()
        },
        Settings {
            job_ttl_ms: 0,
            ..Settings::default()
        },
    ] {
        assert!(broken.validate().is_err());
    }
    assert!(Settings::default().validate().is_ok());
}

#[test]
fn pressure_scales_capacity_down_and_never_below_one() -> Result<(), McpError> {
    let base = Settings::default();
    assert_eq!(base.for_pressure(0)?, base);
    let high = base.for_pressure(2)?;
    assert_eq!(high.max_in_flight, base.max_in_flight / 2);
    assert_eq!(high.max_jobs, base.max_jobs / 2);
    assert_eq!(high.request_timeout_ms, base.request_timeout_ms);
    let critical = base.for_pressure(99)?;
    assert_eq!(critical.max_in_flight, base.max_in_flight / 4);
    let tiny = Settings {
        max_in_flight: 1,
        ..Settings::default()
    };
    assert_eq!(tiny.for_pressure(3)?.max_in_flight, 1);
    let bad = Settings {
        pressure_scale_pct: [100, 0, 50, 25],
        ..Settings::default()
    };
    assert!(bad.validate().is_err());
    Ok(())
}
