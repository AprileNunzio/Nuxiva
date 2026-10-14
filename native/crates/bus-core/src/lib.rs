#![forbid(unsafe_code)]

mod router;
mod spike;
mod topic;

pub use router::{MAX_SUBSCRIPTIONS, RouterError, SubscriptionId, TopicRouter};
pub use spike::{
    DEFAULT_BUFFER_SIZE, RingBufferLockFree, SynapticSpike, SynapticWeightMatrix, TransmitterType,
};
pub use topic::{
    MAX_DEPTH, MAX_ORIGIN_LEN, MAX_SEGMENT_LEN, Pattern, Segment, Topic, TopicError, matches,
    valid_origin, valid_pattern, valid_topic,
};
