use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum DeviceSelectionMode {
    HierarchicalFallback,
    MultiMicProximity,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AudioDevice {
    pub id: String,
    pub name_key: String,
    pub priority: u8,
    pub is_connected: bool,
    pub is_bluetooth: bool,
    pub battery_level: Option<u8>,
}

impl AudioDevice {
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        name_key: impl Into<String>,
        priority: u8,
        is_connected: bool,
        is_bluetooth: bool,
        battery_level: Option<u8>,
    ) -> Self {
        Self {
            id: id.into(),
            name_key: name_key.into(),
            priority,
            is_connected,
            is_bluetooth,
            battery_level,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SatelliteAudioReport {
    pub satellite_id: String,
    pub timestamp_ms: u64,
    pub snr_db: f32,
    pub energy_rms: f32,
    pub speech_confidence: f32,
}

impl SatelliteAudioReport {
    #[must_use]
    pub fn new(
        satellite_id: impl Into<String>,
        timestamp_ms: u64,
        snr_db: f32,
        energy_rms: f32,
        speech_confidence: f32,
    ) -> Self {
        Self {
            satellite_id: satellite_id.into(),
            timestamp_ms,
            snr_db,
            energy_rms,
            speech_confidence,
        }
    }

    #[must_use]
    pub fn compute_proximity_score(&self) -> f32 {
        let snr_weight = self.snr_db.clamp(0.0, 50.0) * 0.45;
        let energy_weight = (self.energy_rms * 100.0).clamp(0.0, 50.0) * 0.35;
        let conf_weight = self.speech_confidence.clamp(0.0, 1.0) * 20.0;
        snr_weight + energy_weight + conf_weight
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct FailoverDeviceRouter {
    devices: Vec<AudioDevice>,
    mode: DeviceSelectionMode,
    active_device_id: Option<String>,
}

impl Default for FailoverDeviceRouter {
    fn default() -> Self {
        Self::new(DeviceSelectionMode::HierarchicalFallback)
    }
}

impl FailoverDeviceRouter {
    #[must_use]
    pub const fn new(mode: DeviceSelectionMode) -> Self {
        Self {
            devices: Vec::new(),
            mode,
            active_device_id: None,
        }
    }

    pub fn set_mode(&mut self, mode: DeviceSelectionMode) {
        self.mode = mode;
    }

    #[must_use]
    pub const fn mode(&self) -> DeviceSelectionMode {
        self.mode
    }

    pub fn register_device(&mut self, device: AudioDevice) {
        self.devices.retain(|d| d.id != device.id);
        self.devices.push(device);
        self.devices.sort_by_key(|d| d.priority);
    }

    pub fn update_connection_state(&mut self, device_id: &str, is_connected: bool) {
        if let Some(dev) = self.devices.iter_mut().find(|d| d.id == device_id) {
            dev.is_connected = is_connected;
        }
    }

    pub fn resolve_active_device(&mut self) -> Option<&AudioDevice> {
        let elected = self
            .devices
            .iter()
            .find(|d| d.is_connected)
            .map(|d| d.id.clone());

        self.active_device_id = elected;

        if let Some(ref target_id) = self.active_device_id {
            self.devices.iter().find(|d| &d.id == target_id)
        } else {
            None
        }
    }

    #[must_use]
    pub fn active_device(&self) -> Option<&AudioDevice> {
        if let Some(ref id) = self.active_device_id {
            self.devices.iter().find(|d| &d.id == id)
        } else {
            None
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct MultiMicTriage {
    active_winner_id: Option<String>,
    hysteresis_margin: f32,
    last_winning_score: f32,
}

impl Default for MultiMicTriage {
    fn default() -> Self {
        Self::new(3.5)
    }
}

impl MultiMicTriage {
    #[must_use]
    pub const fn new(hysteresis_margin: f32) -> Self {
        Self {
            active_winner_id: None,
            hysteresis_margin,
            last_winning_score: 0.0,
        }
    }

    pub fn elect_best_source(&mut self, reports: &[SatelliteAudioReport]) -> Option<String> {
        if reports.is_empty() {
            return self.active_winner_id.clone();
        }

        let mut best_id: Option<String> = None;
        let mut best_score = -1.0_f32;

        for report in reports {
            let score = report.compute_proximity_score();
            if score > best_score {
                best_score = score;
                best_id = Some(report.satellite_id.clone());
            }
        }

        if let Some(curr_winner) = &self.active_winner_id {
            if let Some(new_candidate) = &best_id {
                if new_candidate == curr_winner {
                    self.last_winning_score = best_score;
                } else if best_score > (self.last_winning_score + self.hysteresis_margin) {
                    self.active_winner_id = Some(new_candidate.clone());
                    self.last_winning_score = best_score;
                }
            }
        } else if let Some(new_candidate) = best_id {
            self.active_winner_id = Some(new_candidate);
            self.last_winning_score = best_score;
        }

        self.active_winner_id.clone()
    }

    pub fn reset(&mut self) {
        self.active_winner_id = None;
        self.last_winning_score = 0.0;
    }
}
