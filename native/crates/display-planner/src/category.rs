use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Category {
    Safety,
    Conversation,
    Personal,
    Home,
    Work,
    Media,
    Info,
    System,
    Ambient,
}

impl Category {
    #[must_use]
    pub const fn weight(self) -> f32 {
        match self {
            Self::Safety => 1.0,
            Self::Conversation => 0.95,
            Self::Personal => 0.85,
            Self::Home => 0.75,
            Self::Work => 0.7,
            Self::Media => 0.65,
            Self::Info => 0.5,
            Self::System => 0.4,
            Self::Ambient => 0.2,
        }
    }
}

const TABLE: [(&str, Category); 74] = [
    ("active_tasks", Category::Work),
    ("alarm", Category::Safety),
    ("alert_error", Category::Safety),
    ("alert_info", Category::Safety),
    ("alert_warning", Category::Safety),
    ("api_costs", Category::System),
    ("audio_spectrum", Category::Media),
    ("brief", Category::Personal),
    ("calculator", Category::Info),
    ("cam_stream", Category::Home),
    ("chess_3d", Category::Media),
    ("cicd_tracker", Category::Work),
    ("clipboard_sync", Category::Work),
    ("clock", Category::Ambient),
    ("code_view", Category::Work),
    ("common", Category::Info),
    ("contact_card", Category::Personal),
    ("context_window", Category::System),
    ("crypto_ticker", Category::Info),
    ("cyber_alert", Category::Safety),
    ("diorama", Category::Ambient),
    ("docker_matrix", Category::System),
    ("document_viewer", Category::Work),
    ("energy_chart", Category::Home),
    ("expert_work", Category::Work),
    ("f1_race", Category::Info),
    ("firewall_logs", Category::System),
    ("g_notify", Category::Personal),
    ("git_diff", Category::Work),
    ("health_hub", Category::Personal),
    ("hockey_match", Category::Info),
    ("home_rooms", Category::Home),
    ("kanban_board", Category::Work),
    ("karaoke", Category::Media),
    ("lan_device", Category::System),
    ("lavagna", Category::Work),
    ("listening", Category::Conversation),
    ("live_cam", Category::Home),
    ("mood_aura", Category::Personal),
    ("music", Category::Media),
    ("net_topology", Category::System),
    ("network_devices", Category::System),
    ("notice", Category::Info),
    ("os_networks", Category::System),
    ("people_seen", Category::Personal),
    ("pomodoro", Category::Work),
    ("port_scanner", Category::System),
    ("rag_sources", Category::Conversation),
    ("reminder", Category::Personal),
    ("repair_workbench", Category::Work),
    ("route", Category::Personal),
    ("sport_match", Category::Info),
    ("sport_table", Category::Info),
    ("ssh_sessions", Category::System),
    ("study", Category::Work),
    ("studio_3d", Category::Work),
    ("subsystem_alert", Category::Safety),
    ("sun_cycle", Category::Ambient),
    ("sync_pulse", Category::Personal),
    ("system_health", Category::System),
    ("system_monitor", Category::System),
    ("system_update", Category::System),
    ("text_long", Category::Conversation),
    ("text_short", Category::Conversation),
    ("thermostat", Category::Home),
    ("thinking_tree", Category::Conversation),
    ("tv_player", Category::Media),
    ("usb_monitor", Category::System),
    ("vital_check", Category::Personal),
    ("viewer_3d", Category::Work),
    ("molecule_viewer", Category::Work),
    ("voices_ready", Category::System),
    ("vram_allocator", Category::System),
    ("weather", Category::Info),
];

#[must_use]
pub fn category_of(widget: &str) -> Category {
    TABLE
        .iter()
        .find(|(id, _)| *id == widget)
        .map_or(Category::Info, |(_, c)| *c)
}

pub fn known_widgets() -> impl Iterator<Item = &'static str> {
    TABLE.iter().map(|(id, _)| *id)
}
