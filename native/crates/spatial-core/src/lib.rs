#![forbid(unsafe_code)]

pub mod arbiter;
pub mod co_pilot;
pub mod deferred_queue;
pub mod intent_router;
pub mod manifest;
pub mod memory_cache;
pub mod morphology;
pub mod network_governor;
pub mod priority;
pub mod resource_governor;
pub mod task_governor;
pub mod workbench_netlist;
pub mod workbench_stability;
pub mod workbench_tracker;
pub mod z_stack;

pub use workbench_netlist::{
    NetlistIssue, NetlistIssueKind, NetlistNet, PinReference, validate_netlist,
};
pub use workbench_stability::{SceneState, StabilityGate};
pub use workbench_tracker::{BoundingBox, ComponentTracker, Detection, TrackedComponent};

pub use arbiter::{ArbitrationAction, ArbitrationResult, PriorityArbiter};
pub use co_pilot::{CoPilotAction, CoPilotActionKind, LiveCoPilotEngine};
pub use deferred_queue::{DeferredQueue, MAX_DEFERRED_EVENTS};
pub use intent_router::IntentRouter;
pub use manifest::{
    AssistantRequirement, ContextManifest, FocusLockLevel, GpuLoad, SafeZone, ViewportMode,
    VoiceInteraction,
};
pub use memory_cache::{FastSemanticMemory, MemoryEntry, MemoryHit};
pub use morphology::AssistantMorphology;
pub use network_governor::{
    ActiveRouteResult, ConnectionRoutingPolicy, GsmModem, InterfaceKind, IpAssignmentMode,
    NetworkGovernor, NetworkInterface, NodeNetworkProfile, VpnTunnel,
};
pub use priority::{NotificationEvent, NotificationPriority};
pub use resource_governor::{
    ComputeProvider, LocalEngineAction, RemoteServerEntry, ResourceGovernor, ResourcePlan,
    TargetAllocation,
};
pub use task_governor::{
    MeshDispatchResolution, MeshTaskGovernor, NodeComponent, NodeProfile, TechnicalEvaluation,
};
pub use z_stack::{ZLayer, ZLayerStack, ZLayerState};

#[cfg(test)]
mod tests;
