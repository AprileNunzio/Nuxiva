#![forbid(unsafe_code)]

pub mod ai_engine;
pub mod automations;
pub mod engines;
pub mod firewall;
pub mod memory;
pub mod network;
pub mod nodes;
pub mod notification;
pub mod options;
pub mod peripherals;
pub mod process;
pub mod status;
pub mod subapps;
pub mod surveillance;

pub use ai_engine::{
    AiEngineManager, AiEngineStatus, InferenceConfig, InferenceTelemetry, ModelKind, ModelProfile,
    ModelQuantization,
};
pub use automations::{
    ActionKind, AutomationEngine, AutomationRule, AutomationsSummary, LawRule, LawTier, TriggerKind,
};
pub use engines::{EngineFamily, EngineManifest, EngineOption, EngineRegistry};
pub use firewall::{
    BlockedAddress, FirewallEngine, FirewallMode, FirewallRule, RuleAction, RuleDirection,
    RuleProtocol,
};
pub use memory::{MemoryManager, MemoryState};
pub use network::{AdapterKind, NetworkAdapter, NetworkManager};
pub use nodes::{HardwareTarget, NodeInfo, NodeManager, NodeStatus, NodeTier, NodesSummary};
pub use notification::{NotificationItem, NotificationLevel, NotificationManager};
pub use options::{OptionCategory, SystemOption, SystemOptionsRegistry};
pub use peripherals::{
    DeviceKind, PeripheralDevice, PeripheralsManager, PeripheralsSummary, StorePackageMeta,
};
pub use process::{ProcessInfo, ProcessManager, ProcessStatus};
pub use status::{HealthStatus, SystemStatus, calculate_system_status};
pub use subapps::{MacroAppManifest, SubappManifest, SubappRegistry};
pub use surveillance::{
    CameraConfig, CameraKind, CameraTelemetry, StreamState, SurveillanceManager,
};

