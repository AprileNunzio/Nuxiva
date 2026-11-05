#![forbid(unsafe_code)]

pub mod ai_engine;
pub mod firewall;
pub mod memory;
pub mod network;
pub mod nodes;
pub mod notification;
pub mod process;
pub mod status;

pub use ai_engine::{
    AiEngineManager, AiEngineStatus, InferenceConfig, InferenceTelemetry, ModelKind, ModelProfile,
    ModelQuantization,
};
pub use firewall::{
    BlockedAddress, FirewallEngine, FirewallMode, FirewallRule, RuleAction, RuleDirection,
    RuleProtocol,
};
pub use memory::{MemoryManager, MemorySample, MemoryState};
pub use network::{AdapterKind, NetworkAdapter, NetworkManager};
pub use nodes::{HardwareTarget, NodeInfo, NodeManager, NodeStatus, NodeTier, NodesSummary};
pub use notification::{NotificationItem, NotificationLevel, NotificationManager};
pub use process::{ProcessInfo, ProcessManager, ProcessStatus};
pub use status::{HealthStatus, SystemStatus, calculate_system_status};
