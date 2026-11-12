#![forbid(unsafe_code)]
#![allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_possible_wrap,
    clippy::cast_sign_loss,
    clippy::cast_lossless,
    clippy::must_use_candidate,
    clippy::missing_errors_doc,
    clippy::similar_names,
    clippy::module_name_repetitions,
    clippy::manual_let_else,
    clippy::return_self_not_must_use,
    clippy::checked_conversions,
    clippy::too_many_lines,
    clippy::wildcard_imports,
    clippy::unreadable_literal
)]

pub mod bridge;
pub mod fabric;
pub mod interaction;
pub mod model;
pub mod spec;
pub mod tlv;

pub use bridge::{BridgedDeviceKind, BridgedEntity, MatterBridge};
pub use fabric::{AccessControlEntry, AclPrivilege, FabricTable, MatterFabric};
pub use interaction::{
    InteractionAction, InteractionRequest, InteractionResponse, InteractionStatus,
    dispatch_interaction,
};
pub use model::{MatterAttribute, MatterAttributeValue, MatterCluster, MatterEndpoint, MatterNode};
pub use spec::*;
pub use tlv::{
    TlvDecoder, TlvElement, TlvEncoder, TlvError, TlvTag, TlvValue, decode_tlv, encode_tlv,
};
