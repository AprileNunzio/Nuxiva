#![forbid(unsafe_code)]

mod admin_os;
mod arbitration;
mod audio;
mod bus;
mod cortex;
mod display;
mod embodied;
mod errors;
mod gesture;
mod governors;
mod language;
mod memory;
mod mesh;
mod presence;
mod scanner;
mod signal;
mod stage;
mod token;
mod topics;
mod update;
mod vitals;
mod workbench;

use admin_os::{
    RustAdminOsAiEngine, RustAdminOsFirewall, RustAdminOsMemory, RustAdminOsNotification,
};
use arbitration::{RustIntentRouter, RustSpatialArbiter};
use audio::{RustAudioCleaner, RustDeviceRouter, RustMultiMicTriage};
use bus::{PySynapticSpike, RustSynapticBus, SynapticWeightMatrix};
use cortex::{
    CortexError, RustContextGraph, RustNeuronIndex, RustSigner, cortex_derive_key,
    cortex_generate_key, cortex_open, cortex_sanitize_identifier, cortex_sanitize_utterance,
    cortex_seal, cortex_validate_slots, cortex_verify,
};
use display::{display_apply, display_diff};
use embodied::{
    RustCorticalCortex, RustEmbodiedCortex, RustEpistemicDoubtEngine, RustFieldbusController,
    RustHumanoidKinematics34, RustOntologicalCreativeEngine,
};
use gesture::{RustGestureEngine, gesture_catalog, gesture_validate_profile};
use governors::{RustMeshTaskGovernor, RustNetworkGovernor, RustResourceGovernor};
use language::{detect_language, supported_languages};
use memory::{RustFastMemory, RustLiveCoPilot};
use mesh::{RustCrdtMesh, RustGossipMesh, RustP2PStreamManager};
use presence::RustPresenceTracker;
use pyo3::prelude::*;
use scanner::FastScanner;
use signal::{RustSignalEnhancer, RustVoiceBiomarkers};
use stage::{RustParticleCache, particles_count, particles_sample, stage_plan};
use token::{RustTokenCodec, TokenRejected};
use topics::{TopicRouter, matches, valid_origin, valid_pattern, valid_topic};
use update::{
    update_changelog, update_impact, update_pipeline_advance, update_signature, update_valid_rev,
    update_verify_tree,
};
use vitals::vitals_parse_ble_heart_rate;

#[pymodule(gil_used = false)]
fn nuxiva_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("MAX_SUBSCRIPTIONS", nuxiva_bus_core::MAX_SUBSCRIPTIONS)?;
    m.add_class::<TopicRouter>()?;
    m.add_function(wrap_pyfunction!(display_diff, m)?)?;
    m.add_function(wrap_pyfunction!(display_apply, m)?)?;
    m.add_class::<RustPresenceTracker>()?;
    m.add_class::<RustTokenCodec>()?;
    m.add("TokenRejected", m.py().get_type::<TokenRejected>())?;
    m.add_class::<RustSynapticBus>()?;
    m.add_class::<SynapticWeightMatrix>()?;
    m.add_class::<PySynapticSpike>()?;
    m.add_class::<FastScanner>()?;
    m.add_class::<RustCrdtMesh>()?;
    m.add_class::<RustP2PStreamManager>()?;
    m.add_class::<RustGossipMesh>()?;
    m.add_class::<RustSpatialArbiter>()?;
    m.add_class::<RustIntentRouter>()?;
    m.add_class::<RustAudioCleaner>()?;
    m.add_class::<RustDeviceRouter>()?;
    m.add_class::<RustMultiMicTriage>()?;
    m.add_class::<RustSignalEnhancer>()?;
    m.add_class::<RustVoiceBiomarkers>()?;
    m.add_class::<RustGestureEngine>()?;
    m.add_class::<RustFastMemory>()?;
    m.add_class::<RustLiveCoPilot>()?;
    m.add_class::<RustResourceGovernor>()?;
    m.add_class::<RustMeshTaskGovernor>()?;
    m.add_class::<RustNetworkGovernor>()?;
    m.add_class::<workbench::RustWorkbenchTracker>()?;
    m.add_class::<RustNeuronIndex>()?;
    m.add_class::<RustContextGraph>()?;
    m.add_class::<RustCorticalCortex>()?;
    m.add_class::<RustEmbodiedCortex>()?;
    m.add_class::<RustEpistemicDoubtEngine>()?;
    m.add_class::<RustOntologicalCreativeEngine>()?;
    m.add_class::<RustHumanoidKinematics34>()?;
    m.add_class::<RustFieldbusController>()?;
    m.add_class::<RustSigner>()?;
    m.add_class::<RustParticleCache>()?;
    m.add_class::<RustAdminOsMemory>()?;
    m.add_class::<RustAdminOsNotification>()?;
    m.add_class::<RustAdminOsAiEngine>()?;
    m.add_class::<RustAdminOsFirewall>()?;
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
    m.add_function(wrap_pyfunction!(stage_plan, m)?)?;
    m.add_function(wrap_pyfunction!(particles_sample, m)?)?;
    m.add_function(wrap_pyfunction!(particles_count, m)?)?;
    m.add_function(wrap_pyfunction!(vitals_parse_ble_heart_rate, m)?)?;
    m.add_function(wrap_pyfunction!(gesture_validate_profile, m)?)?;
    m.add_function(wrap_pyfunction!(gesture_catalog, m)?)?;
    m.add_function(wrap_pyfunction!(update_valid_rev, m)?)?;
    m.add_function(wrap_pyfunction!(update_signature, m)?)?;
    m.add_function(wrap_pyfunction!(update_verify_tree, m)?)?;
    m.add_function(wrap_pyfunction!(update_impact, m)?)?;
    m.add_function(wrap_pyfunction!(update_changelog, m)?)?;
    m.add_function(wrap_pyfunction!(update_pipeline_advance, m)?)?;
    Ok(())
}
