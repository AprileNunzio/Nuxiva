#![forbid(unsafe_code)]

pub mod memory;
pub mod notification;
pub mod process;
pub mod status;

pub use memory::{MemoryManager, MemorySample, MemoryState};
pub use notification::{NotificationItem, NotificationLevel, NotificationManager};
pub use process::{ProcessInfo, ProcessManager, ProcessStatus};
pub use status::{HealthStatus, SystemStatus, calculate_system_status};
