use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CameraKind {
    Webcam,
    Rtsp,
    Rtsps,
    Onvif,
    Hikvision,
}

impl CameraKind {
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s.trim().to_ascii_lowercase().as_str() {
            "webcam" | "local" => Some(Self::Webcam),
            "rtsp" => Some(Self::Rtsp),
            "rtsps" => Some(Self::Rtsps),
            "onvif" => Some(Self::Onvif),
            "hikvision" => Some(Self::Hikvision),
            _ => None,
        }
    }

    #[must_use]
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Webcam => "webcam",
            Self::Rtsp => "rtsp",
            Self::Rtsps => "rtsps",
            Self::Onvif => "onvif",
            Self::Hikvision => "hikvision",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum StreamState {
    Offline,
    Connecting,
    Live,
    Degraded,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CameraConfig {
    pub id: String,
    pub name: String,
    pub kind: CameraKind,
    pub url: String,
    pub enabled: bool,
    pub record: bool,
    pub consent: bool,
    pub retention_min: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CameraTelemetry {
    pub id: String,
    pub state: StreamState,
    pub fps: u32,
    pub width: u32,
    pub height: u32,
    pub last_frame_timestamp_ms: u64,
}

#[derive(Debug, Default)]
pub struct SurveillanceManager {
    cameras: HashMap<String, CameraConfig>,
    telemetry: HashMap<String, CameraTelemetry>,
}

impl SurveillanceManager {
    #[must_use]
    pub fn new() -> Self {
        Self {
            cameras: HashMap::new(),
            telemetry: HashMap::new(),
        }
    }

    #[must_use]
    pub fn sanitize_name(name: &str) -> String {
        name.trim()
            .chars()
            .filter(|c| !c.is_control())
            .take(60)
            .collect()
    }

    #[must_use]
    pub fn validate_source_id(source_id: &str) -> bool {
        let trimmed = source_id.trim();
        if trimmed.len() != 10 {
            return false;
        }
        let prefix = &trimmed[0..2];
        if prefix != "w-" && prefix != "c-" && prefix != "i-" {
            return false;
        }
        trimmed[2..].chars().all(|c| c.is_ascii_hexdigit())
    }

    pub fn validate_stream_url(kind: CameraKind, url: &str) -> Result<String, &'static str> {
        let trimmed = url.trim();
        if trimmed.is_empty() {
            return Err("empty_url");
        }
        if trimmed.len() > 300 {
            return Err("url_too_long");
        }
        if trimmed.chars().any(char::is_whitespace) {
            return Err("whitespace_in_url");
        }

        match kind {
            CameraKind::Webcam => {
                if trimmed == "0" || trimmed.starts_with("/dev/video") {
                    Ok(trimmed.to_string())
                } else {
                    Err("invalid_webcam_device")
                }
            }
            CameraKind::Rtsp | CameraKind::Onvif | CameraKind::Hikvision => {
                let lower = trimmed.to_ascii_lowercase();
                if lower.starts_with("rtsp://")
                    || lower.starts_with("rtsps://")
                    || lower.starts_with("http://")
                    || lower.starts_with("https://")
                {
                    Ok(trimmed.to_string())
                } else {
                    Err("invalid_stream_protocol")
                }
            }
            CameraKind::Rtsps => {
                let lower = trimmed.to_ascii_lowercase();
                if lower.starts_with("rtsps://") {
                    Ok(trimmed.to_string())
                } else {
                    Err("must_use_rtsps_protocol")
                }
            }
        }
    }

    pub fn register_camera(&mut self, config: CameraConfig) -> Result<(), &'static str> {
        let sanitized_name = Self::sanitize_name(&config.name);
        if sanitized_name.is_empty() {
            return Err("empty_name");
        }
        let validated_url = Self::validate_stream_url(config.kind, &config.url)?;

        let mut ready = config;
        ready.name = sanitized_name;
        ready.url = validated_url;
        let id = ready.id.clone();

        self.telemetry.insert(
            id.clone(),
            CameraTelemetry {
                id: id.clone(),
                state: if ready.enabled {
                    StreamState::Connecting
                } else {
                    StreamState::Offline
                },
                fps: 0,
                width: 0,
                height: 0,
                last_frame_timestamp_ms: 0,
            },
        );

        self.cameras.insert(id, ready);
        Ok(())
    }

    pub fn remove_camera(&mut self, id: &str) -> Option<CameraConfig> {
        self.telemetry.remove(id);
        self.cameras.remove(id)
    }

    #[must_use]
    pub fn get_camera(&self, id: &str) -> Option<&CameraConfig> {
        self.cameras.get(id)
    }

    #[must_use]
    pub fn list_cameras(&self) -> Vec<CameraConfig> {
        self.cameras.values().cloned().collect()
    }

    pub fn update_telemetry(&mut self, telemetry: CameraTelemetry) {
        if self.cameras.contains_key(&telemetry.id) {
            self.telemetry.insert(telemetry.id.clone(), telemetry);
        }
    }

    #[must_use]
    pub fn active_count(&self) -> usize {
        self.cameras.values().filter(|c| c.enabled).count()
    }

    #[must_use]
    pub fn recording_count(&self) -> usize {
        self.cameras
            .values()
            .filter(|c| c.enabled && c.record && c.consent)
            .count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_camera_kind_parsing() {
        assert_eq!(CameraKind::parse("rtsp"), Some(CameraKind::Rtsp));
        assert_eq!(CameraKind::parse("RTSPS"), Some(CameraKind::Rtsps));
        assert_eq!(CameraKind::parse("webcam"), Some(CameraKind::Webcam));
        assert_eq!(CameraKind::parse("local"), Some(CameraKind::Webcam));
        assert_eq!(CameraKind::parse("onvif"), Some(CameraKind::Onvif));
        assert_eq!(CameraKind::parse("hikvision"), Some(CameraKind::Hikvision));
        assert_eq!(CameraKind::parse("unknown"), None);
    }

    #[test]
    fn test_source_id_validation() {
        assert!(SurveillanceManager::validate_source_id("w-01234567"));
        assert!(SurveillanceManager::validate_source_id("c-abcdef12"));
        assert!(SurveillanceManager::validate_source_id("i-deadbeef"));
        assert!(!SurveillanceManager::validate_source_id("x-deadbeef"));
        assert!(!SurveillanceManager::validate_source_id("c-toolong12345"));
        assert!(!SurveillanceManager::validate_source_id(""));
    }

    #[test]
    fn test_url_validation_zero_trust() {
        assert!(SurveillanceManager::validate_stream_url(
            CameraKind::Rtsp,
            "rtsp://192.168.1.100:554/live"
        )
        .is_ok());
        assert!(SurveillanceManager::validate_stream_url(
            CameraKind::Rtsps,
            "rtsps://camera.local/stream"
        )
        .is_ok());
        assert!(SurveillanceManager::validate_stream_url(
            CameraKind::Rtsps,
            "rtsp://camera.local/stream"
        )
        .is_err());
        assert!(SurveillanceManager::validate_stream_url(CameraKind::Webcam, "0").is_ok());
        assert!(
            SurveillanceManager::validate_stream_url(CameraKind::Webcam, "/dev/video0").is_ok()
        );
        assert!(
            SurveillanceManager::validate_stream_url(CameraKind::Webcam, "http://bad").is_err()
        );
        assert!(SurveillanceManager::validate_stream_url(
            CameraKind::Rtsp,
            "rtsp://bad url with space"
        )
        .is_err());
    }

    #[test]
    fn test_manager_registration_and_stats() {
        let mut mgr = SurveillanceManager::new();
        let cam1 = CameraConfig {
            id: "cam-1".to_string(),
            name: "Front Door".to_string(),
            kind: CameraKind::Rtsp,
            url: "rtsp://10.0.0.1/live".to_string(),
            enabled: true,
            record: true,
            consent: true,
            retention_min: 60,
        };
        let cam2 = CameraConfig {
            id: "cam-2".to_string(),
            name: "Backyard".to_string(),
            kind: CameraKind::Webcam,
            url: "0".to_string(),
            enabled: true,
            record: false,
            consent: true,
            retention_min: 5,
        };

        assert!(mgr.register_camera(cam1).is_ok());
        assert!(mgr.register_camera(cam2).is_ok());

        assert_eq!(mgr.list_cameras().len(), 2);
        assert_eq!(mgr.active_count(), 2);
        assert_eq!(mgr.recording_count(), 1);

        assert!(mgr.remove_camera("cam-1").is_some());
        assert_eq!(mgr.list_cameras().len(), 1);
        assert_eq!(mgr.recording_count(), 0);
    }
}
