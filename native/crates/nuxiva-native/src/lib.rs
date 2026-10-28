#![forbid(unsafe_code)]

mod arbitration;
mod audio;
mod bus;
mod cortex;
mod embodied;
mod errors;
mod governors;
mod language;
mod memory;
mod mesh;
mod scanner;
mod topics;
mod workbench;

use arbitration::{RustIntentRouter, RustSpatialArbiter};
use audio::{RustAudioCleaner, RustDeviceRouter, RustMultiMicTriage};
use bus::{PySynapticSpike, RustSynapticBus, SynapticWeightMatrix};
use cortex::{
    CortexError, RustNeuronIndex, RustSigner, cortex_derive_key, cortex_generate_key, cortex_open,
    cortex_sanitize_identifier, cortex_sanitize_utterance, cortex_seal, cortex_validate_slots,
    cortex_verify,
};
use embodied::{RustCorticalCortex, RustEmbodiedCortex};
use governors::{RustMeshTaskGovernor, RustNetworkGovernor, RustResourceGovernor};
use language::{detect_language, supported_languages};
use memory::{RustFastMemory, RustLiveCoPilot};
use mesh::{RustCrdtMesh, RustP2PStreamManager};
use pyo3::prelude::*;
use scanner::FastScanner;
use topics::{TopicRouter, matches, valid_origin, valid_pattern, valid_topic};

#[pymodule(gil_used = false)]
fn nuxiva_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("MAX_SUBSCRIPTIONS", nuxiva_bus_core::MAX_SUBSCRIPTIONS)?;
    m.add_class::<TopicRouter>()?;
    m.add_class::<RustSynapticBus>()?;
    m.add_class::<SynapticWeightMatrix>()?;
    m.add_class::<PySynapticSpike>()?;
    m.add_class::<FastScanner>()?;
    m.add_class::<RustCrdtMesh>()?;
    m.add_class::<RustP2PStreamManager>()?;
    m.add_class::<RustSpatialArbiter>()?;
    m.add_class::<RustIntentRouter>()?;
    m.add_class::<RustAudioCleaner>()?;
    m.add_class::<RustDeviceRouter>()?;
    m.add_class::<RustMultiMicTriage>()?;
    m.add_class::<RustFastMemory>()?;
    m.add_class::<RustLiveCoPilot>()?;
    m.add_class::<RustResourceGovernor>()?;
    m.add_class::<RustMeshTaskGovernor>()?;
    m.add_class::<RustNetworkGovernor>()?;
    m.add_class::<workbench::RustWorkbenchTracker>()?;
    m.add_class::<RustNeuronIndex>()?;
    m.add_class::<RustCorticalCortex>()?;
    m.add_class::<RustEmbodiedCortex>()?;
    m.add_class::<RustSigner>()?;
    m.add("CortexError", m.py().get_type::<CortexError>())?;
    m.add_function(wrap_pyfunction!(cortex_sanitize_utterance, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_sanitize_identifier, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_generate_key, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_derive_key, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_seal, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_open, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_verify, m)?)?;
    m.add_function(wrap_pyfunction!(cortex_validate_slots, m)?)?;
    m.add_function(wrap_pyfunction!(workbench::validate_netlist_json, m)?)?;
    m.add_function(wrap_pyfunction!(matches, m)?)?;
    m.add_function(wrap_pyfunction!(valid_topic, m)?)?;
    m.add_function(wrap_pyfunction!(valid_pattern, m)?)?;
    m.add_function(wrap_pyfunction!(valid_origin, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language, m)?)?;
    m.add_function(wrap_pyfunction!(supported_languages, m)?)?;
    Ok(())
}
