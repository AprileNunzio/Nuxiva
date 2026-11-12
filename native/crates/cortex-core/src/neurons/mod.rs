pub mod r_stdp;
pub mod sdr;
pub mod spiking;

pub use r_stdp::{RStdpConfig, RewardModulatedStdpSynapse};
pub use sdr::{SDR_BIT_SIZE, SDR_DEFAULT_K, SDR_WORD_COUNT, SparseDistributedRepresentation};
pub use spiking::{AdaptiveSpikingNeuron, CompartmentInput, IzhikevichParams, SpikingNeuronState};
