use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OptionCategory {
    Multimedia,
    Security,
    AiVoice,
    DisplayKiosk,
    Privacy,
    System,
}

impl OptionCategory {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Multimedia => "multimedia",
            Self::Security => "security",
            Self::AiVoice => "ai_voice",
            Self::DisplayKiosk => "display_kiosk",
            Self::Privacy => "privacy",
            Self::System => "system",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SystemOption {
    pub id: String,
    pub category: OptionCategory,
    pub enabled: bool,
    pub default_enabled: bool,
    pub icon: String,
    pub title_key: String,
    pub description_key: String,
    #[serde(default)]
    pub tags: Vec<String>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct SystemOptionsRegistry {
    options: HashMap<String, SystemOption>,
}

impl SystemOptionsRegistry {
    #[must_use]
    pub fn new() -> Self {
        let mut registry = Self {
            options: HashMap::new(),
        };
        registry.register_default_options();
        registry
    }

    #[allow(clippy::too_many_lines)]
    fn register_default_options(&mut self) {
        let defaults = vec![
            SystemOption {
                id: "multimedia_music_display_on_screen".to_string(),
                category: OptionCategory::Multimedia,
                enabled: true,
                default_enabled: true,
                icon: "Music".to_string(),
                title_key: "opt_music_display_title".to_string(),
                description_key: "opt_music_display_desc".to_string(),
                tags: vec![
                    "canzone".to_string(),
                    "musica".to_string(),
                    "schermo".to_string(),
                    "audio".to_string(),
                ],
            },
            SystemOption {
                id: "multimedia_music_recognition".to_string(),
                category: OptionCategory::Multimedia,
                enabled: true,
                default_enabled: true,
                icon: "Mic".to_string(),
                title_key: "opt_music_recognition_title".to_string(),
                description_key: "opt_music_recognition_desc".to_string(),
                tags: vec![
                    "riconoscimento".to_string(),
                    "fingerprint".to_string(),
                    "shazam".to_string(),
                ],
            },
            SystemOption {
                id: "security_alarm_system".to_string(),
                category: OptionCategory::Security,
                enabled: false,
                default_enabled: false,
                icon: "ShieldAlert".to_string(),
                title_key: "opt_alarm_system_title".to_string(),
                description_key: "opt_alarm_system_desc".to_string(),
                tags: vec![
                    "allarme".to_string(),
                    "sicurezza".to_string(),
                    "antintrusione".to_string(),
                ],
            },
            SystemOption {
                id: "security_red_alert".to_string(),
                category: OptionCategory::Security,
                enabled: false,
                default_enabled: false,
                icon: "AlertOctagon".to_string(),
                title_key: "opt_red_alert_title".to_string(),
                description_key: "opt_red_alert_desc".to_string(),
                tags: vec![
                    "allarme rosso".to_string(),
                    "emergenza".to_string(),
                    "blocco".to_string(),
                ],
            },
            SystemOption {
                id: "security_camera_motion_alerts".to_string(),
                category: OptionCategory::Security,
                enabled: true,
                default_enabled: true,
                icon: "Camera".to_string(),
                title_key: "opt_camera_alerts_title".to_string(),
                description_key: "opt_camera_alerts_desc".to_string(),
                tags: vec![
                    "telecamere".to_string(),
                    "movimento".to_string(),
                    "notifiche".to_string(),
                ],
            },
            SystemOption {
                id: "ai_voice_continuous_listening".to_string(),
                category: OptionCategory::AiVoice,
                enabled: true,
                default_enabled: true,
                icon: "Radio".to_string(),
                title_key: "opt_voice_listening_title".to_string(),
                description_key: "opt_voice_listening_desc".to_string(),
                tags: vec![
                    "voce".to_string(),
                    "ascolto".to_string(),
                    "wake word".to_string(),
                ],
            },
            SystemOption {
                id: "ai_voice_speech_feedback".to_string(),
                category: OptionCategory::AiVoice,
                enabled: true,
                default_enabled: true,
                icon: "Volume2".to_string(),
                title_key: "opt_speech_feedback_title".to_string(),
                description_key: "opt_speech_feedback_desc".to_string(),
                tags: vec![
                    "sintesi".to_string(),
                    "audio".to_string(),
                    "tts".to_string(),
                ],
            },
            SystemOption {
                id: "ai_mcp_autonomous_tools".to_string(),
                category: OptionCategory::AiVoice,
                enabled: true,
                default_enabled: true,
                icon: "Cpu".to_string(),
                title_key: "opt_mcp_tools_title".to_string(),
                description_key: "opt_mcp_tools_desc".to_string(),
                tags: vec![
                    "mcp".to_string(),
                    "tool".to_string(),
                    "agenti".to_string(),
                    "autonomia".to_string(),
                ],
            },
            SystemOption {
                id: "display_kiosk_hud".to_string(),
                category: OptionCategory::DisplayKiosk,
                enabled: true,
                default_enabled: true,
                icon: "Monitor".to_string(),
                title_key: "opt_kiosk_hud_title".to_string(),
                description_key: "opt_kiosk_hud_desc".to_string(),
                tags: vec![
                    "hud".to_string(),
                    "kiosk".to_string(),
                    "desktop".to_string(),
                    "widget".to_string(),
                ],
            },
            SystemOption {
                id: "display_song_lyrics_overlay".to_string(),
                category: OptionCategory::DisplayKiosk,
                enabled: true,
                default_enabled: true,
                icon: "Layers".to_string(),
                title_key: "opt_lyrics_overlay_title".to_string(),
                description_key: "opt_lyrics_overlay_desc".to_string(),
                tags: vec![
                    "testi".to_string(),
                    "karaoke".to_string(),
                    "overlay".to_string(),
                ],
            },
            SystemOption {
                id: "privacy_vitals_tracking".to_string(),
                category: OptionCategory::Privacy,
                enabled: false,
                default_enabled: false,
                icon: "Heart".to_string(),
                title_key: "opt_vitals_tracking_title".to_string(),
                description_key: "opt_vitals_tracking_desc".to_string(),
                tags: vec![
                    "vitali".to_string(),
                    "presenza".to_string(),
                    "salute".to_string(),
                ],
            },
        ];

        for opt in defaults {
            self.options.insert(opt.id.clone(), opt);
        }
    }

    pub fn register(&mut self, option: SystemOption) -> Result<(), &'static str> {
        let trimmed_id = option.id.trim().to_ascii_lowercase();
        if trimmed_id.is_empty() || trimmed_id.len() > 64 {
            return Err("INVALID_ID");
        }
        if !trimmed_id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
        {
            return Err("INVALID_ID_CHARS");
        }

        let mut sanitized = option;
        sanitized.id.clone_from(&trimmed_id);
        self.options.insert(trimmed_id, sanitized);
        Ok(())
    }

    pub fn toggle(&mut self, id: &str) -> Result<bool, &'static str> {
        let opt = self.options.get_mut(id).ok_or("OPTION_NOT_FOUND")?;
        opt.enabled = !opt.enabled;
        Ok(opt.enabled)
    }

    pub fn set_state(&mut self, id: &str, enabled: bool) -> Result<(), &'static str> {
        let opt = self.options.get_mut(id).ok_or("OPTION_NOT_FOUND")?;
        opt.enabled = enabled;
        Ok(())
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&SystemOption> {
        self.options.get(id)
    }

    #[must_use]
    pub fn list_all(&self) -> Vec<SystemOption> {
        let mut list: Vec<SystemOption> = self.options.values().cloned().collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    #[must_use]
    pub fn list_by_category(&self, category: OptionCategory) -> Vec<SystemOption> {
        let mut list: Vec<SystemOption> = self
            .options
            .values()
            .filter(|o| o.category == category)
            .cloned()
            .collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    #[must_use]
    pub fn search(&self, query: &str) -> Vec<SystemOption> {
        let q = query.trim().to_lowercase();
        if q.is_empty() {
            return self.list_all();
        }

        let mut list: Vec<SystemOption> = self
            .options
            .values()
            .filter(|o| {
                o.id.contains(&q)
                    || o.title_key.contains(&q)
                    || o.description_key.contains(&q)
                    || o.tags.iter().any(|tag| tag.to_lowercase().contains(&q))
            })
            .cloned()
            .collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    pub fn scan_directory<P: AsRef<Path>>(
        &mut self,
        root_path: P,
    ) -> Result<usize, std::io::Error> {
        let mut count = 0;
        let path = root_path.as_ref();
        if !path.exists() || !path.is_dir() {
            return Ok(0);
        }

        self.traverse_dir(path, &mut count)?;
        Ok(count)
    }

    fn traverse_dir(
        &mut self,
        current_dir: &Path,
        count: &mut usize,
    ) -> Result<(), std::io::Error> {
        let options_file = current_dir.join("options.json");
        if options_file.is_file() {
            if let Ok(content) = fs::read_to_string(&options_file) {
                if let Ok(opts) = serde_json::from_str::<Vec<SystemOption>>(&content) {
                    for opt in opts {
                        if self.register(opt).is_ok() {
                            *count = count.saturating_add(1);
                        }
                    }
                }
            }
        }

        for entry in fs::read_dir(current_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_dir() && !entry.file_name().to_string_lossy().starts_with('.') {
                let _ = self.traverse_dir(&path, count);
            }
        }

        Ok(())
    }

    #[must_use]
    pub fn export_state(&self) -> HashMap<String, bool> {
        self.options
            .iter()
            .map(|(k, v)| (k.clone(), v.enabled))
            .collect()
    }

    pub fn import_state(&mut self, state: &HashMap<String, bool>) {
        for (k, &v) in state {
            if let Some(opt) = self.options.get_mut(k) {
                opt.enabled = v;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_options_initialization() {
        let reg = SystemOptionsRegistry::new();
        assert!(reg.get("multimedia_music_display_on_screen").is_some());
        assert!(reg.get("security_alarm_system").is_some());
        if let Some(opt) = reg.get("multimedia_music_display_on_screen") {
            assert!(opt.enabled);
        }
        if let Some(opt) = reg.get("security_alarm_system") {
            assert!(!opt.enabled);
        }
    }

    #[test]
    fn test_toggle_and_set_state() {
        let mut reg = SystemOptionsRegistry::new();
        let toggled = reg.toggle("security_alarm_system");
        assert!(toggled.is_ok());
        if let Some(opt) = reg.get("security_alarm_system") {
            assert!(opt.enabled);
        }

        let updated = reg.set_state("security_alarm_system", false);
        assert!(updated.is_ok());
        if let Some(opt) = reg.get("security_alarm_system") {
            assert!(!opt.enabled);
        }
    }

    #[test]
    fn test_search_options() {
        let reg = SystemOptionsRegistry::new();
        let results = reg.search("canzone");
        assert!(!results.is_empty());
        if let Some(first) = results.first() {
            assert_eq!(first.id, "multimedia_music_display_on_screen");
        }

        let alarm_results = reg.search("allarme");
        assert!(alarm_results.len() >= 2);
    }

    #[test]
    fn test_dynamic_scan_directory() {
        let nanos = match std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
            Ok(d) => d.as_nanos(),
            Err(_) => 0,
        };
        let temp_dir = std::env::temp_dir().join(format!("nuxiva_opts_scan_{nanos}"));
        if fs::create_dir_all(&temp_dir).is_err() {
            return;
        }

        let json_content = r#"[
            {
                "id": "custom_store_plugin_option",
                "category": "system",
                "enabled": false,
                "default_enabled": false,
                "icon": "Plug",
                "title_key": "opt_custom_title",
                "description_key": "opt_custom_desc",
                "tags": ["plugin", "store"]
            }
        ]"#;
        if fs::write(temp_dir.join("options.json"), json_content).is_err() {
            let _ = fs::remove_dir_all(&temp_dir);
            return;
        }

        let mut reg = SystemOptionsRegistry::new();
        let scan_res = reg.scan_directory(&temp_dir);
        assert!(scan_res.is_ok());
        if let Ok(count) = scan_res {
            assert_eq!(count, 1);
            assert!(reg.get("custom_store_plugin_option").is_some());
        }

        let _ = fs::remove_dir_all(&temp_dir);
    }
}
