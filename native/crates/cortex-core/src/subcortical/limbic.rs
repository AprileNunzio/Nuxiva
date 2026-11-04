use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HostSystemTelemetry {
    pub cpu_load_ratio: f64,
    pub cpu_temperature_celsius: f64,
    pub ram_pressure_ratio: f64,
    pub bus_latency_ms: f64,
    pub io_error_rate: f64,
    pub battery_charge_ratio: f64,
}

impl Default for HostSystemTelemetry {
    fn default() -> Self {
        Self {
            cpu_load_ratio: 0.25,
            cpu_temperature_celsius: 45.0,
            ram_pressure_ratio: 0.40,
            bus_latency_ms: 1.2,
            io_error_rate: 0.0,
            battery_charge_ratio: 1.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VisceralState {
    pub homeostatic_stress: f64,
    pub metabolic_drain: f64,
    pub systemic_integrity: f64,
    pub visceral_vector: Vec<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThreatAssessment {
    pub threat_level: f64,
    pub salience_score: f64,
    pub requires_emergency_interrupt: bool,
    pub primary_stressor: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LimbicInteroceptiveCore {
    threat_threshold: f64,
    allostatic_load: f64,
}

impl Default for LimbicInteroceptiveCore {
    fn default() -> Self {
        Self {
            threat_threshold: 0.80,
            allostatic_load: 0.0,
        }
    }
}

impl LimbicInteroceptiveCore {
    #[must_use]
    pub fn new(threat_threshold: f64) -> Self {
        Self {
            threat_threshold,
            allostatic_load: 0.0,
        }
    }

    #[must_use]
    pub fn insula_sample(&self, telemetry: &HostSystemTelemetry) -> VisceralState {
        let thermal_stress = ((telemetry.cpu_temperature_celsius - 40.0) / 45.0).clamp(0.0, 1.0);
        let compute_stress = telemetry.cpu_load_ratio.clamp(0.0, 1.0);
        let memory_stress = telemetry.ram_pressure_ratio.clamp(0.0, 1.0);
        let latency_stress = (telemetry.bus_latency_ms / 50.0).clamp(0.0, 1.0);
        let error_stress = (telemetry.io_error_rate * 10.0).clamp(0.0, 1.0);

        let homeostatic_stress = (thermal_stress * 0.3
            + compute_stress * 0.2
            + memory_stress * 0.2
            + latency_stress * 0.15
            + error_stress * 0.15)
            .clamp(0.0, 1.0);

        let metabolic_drain = (compute_stress * 0.7 + thermal_stress * 0.3).clamp(0.0, 1.0);
        let systemic_integrity = (1.0 - error_stress).clamp(0.0, 1.0);

        let visceral_vector = vec![
            homeostatic_stress,
            metabolic_drain,
            systemic_integrity,
            thermal_stress,
            memory_stress,
        ];

        VisceralState {
            homeostatic_stress,
            metabolic_drain,
            systemic_integrity,
            visceral_vector,
        }
    }

    pub fn amygdala_evaluate(
        &mut self,
        visceral: &VisceralState,
        cognitive_surprise: f64,
    ) -> ThreatAssessment {
        let mut threat =
            (visceral.homeostatic_stress * 0.5 + cognitive_surprise * 0.5).clamp(0.0, 1.0);
        if visceral.systemic_integrity < 0.5 {
            threat = (threat + 0.3).min(1.0);
        }

        self.allostatic_load = (self.allostatic_load * 0.9 + threat * 0.1).clamp(0.0, 1.0);
        let salience = (threat * 0.6 + self.allostatic_load * 0.4).clamp(0.0, 1.0);
        let emergency = threat >= self.threat_threshold;

        let primary_stressor = if visceral.visceral_vector.get(3).copied().unwrap_or(0.0) > 0.8 {
            "critical_thermal_threshold".to_string()
        } else if visceral.systemic_integrity < 0.5 {
            "bus_io_failure".to_string()
        } else if cognitive_surprise > 0.85 {
            "unanticipated_epistemic_discrepancy".to_string()
        } else {
            "nominal_equilibrium".to_string()
        };

        ThreatAssessment {
            threat_level: threat,
            salience_score: salience,
            requires_emergency_interrupt: emergency,
            primary_stressor,
        }
    }
}
