#![forbid(unsafe_code)]

mod access;
mod admin_os;
mod agency_core;
mod agents;
mod arbitration;
mod ask_core;
mod audio;
mod authz;
mod bus;
mod ceo;
mod compute_lease;
mod config;
mod cortex;
mod creations;
mod dialog;
mod dialogue;
mod display;
mod dossier;
mod ear;
mod ear_array;
mod embodied;
mod errors;
mod expr;
mod face;
mod face_look;
mod forma;
mod gait_core;
mod gesture;
mod governors;
mod guard;
mod home_rules;
mod jev;
mod language;
mod learner;
mod matter;
mod memory;
mod mesh;
mod molecule;
mod planner;
mod presence;
mod rescue;
mod rescue_ear;
mod scanner;
mod seal;
mod sentinel;
mod sentinel_memory;
mod signal;
mod stage;
mod supervisor;
mod surface;
mod telemetry;
mod token;
mod topics;
mod transcript;
mod update;
mod vault_media;
mod vitals;
mod voice;
mod workbench;

use access::RustAccessMatrix;
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
use learner::RustLearner;
use memory::{RustFastMemory, RustLiveCoPilot};
use mesh::{RustCrdtMesh, RustGossipMesh, RustP2PStreamManager};
use molecule::molecule_build;
use planner::display_plan;
use presence::RustPresenceTracker;
use pyo3::prelude::*;
use scanner::FastScanner;
use sentinel::RustSentinel;
use signal::{RustSignalEnhancer, RustVoiceBiomarkers};
use stage::{
    RustParticleCache, depth_parallax_reconstruct, gaussian_splat_synthesize,
    neural_radiance_synthesize, particles_count, particles_extract_concept, particles_sample,
    particles_synthesize_spec, stage_plan, visual_agent_execute, visual_catalog_classify,
    visual_route_select,
};
use surface::{RustMoveGuard, surface_audience, surface_layout};
use token::{RustTokenCodec, TokenRejected};
use topics::{TopicRouter, matches, valid_origin, valid_pattern, valid_topic};
use update::{
    update_changelog, update_impact, update_pipeline_advance, update_signature, update_valid_rev,
    update_verify_tree,
};

#[pymodule(gil_used = false)]
#[allow(clippy::too_many_lines)]
fn nuxiva_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("MAX_SUBSCRIPTIONS", nuxiva_bus_core::MAX_SUBSCRIPTIONS)?;
    m.add_class::<TopicRouter>()?;
    m.add_function(wrap_pyfunction!(display_diff, m)?)?;
    m.add_function(wrap_pyfunction!(display_apply, m)?)?;
    m.add_function(wrap_pyfunction!(display_plan, m)?)?;
    m.add_class::<RustPresenceTracker>()?;
    m.add_class::<RustLearner>()?;
    m.add_class::<RustSentinel>()?;
    m.add_class::<RustMoveGuard>()?;
    m.add_function(wrap_pyfunction!(molecule_build, m)?)?;
    m.add_function(wrap_pyfunction!(surface_layout, m)?)?;
    m.add_function(wrap_pyfunction!(surface_audience, m)?)?;
    m.add_class::<RustAccessMatrix>()?;
    m.add_class::<RustTokenCodec>()?;
    m.add("TokenRejected", m.py().get_type::<TokenRejected>())?;
    agency_core::register(m)?;
    guard::register(m)?;
    compute_lease::register(m)?;
    jev::register(m)?;
    seal::register(m)?;
    config::register(m)?;
    telemetry::register(m)?;
    supervisor::register(m)?;
    authz::register(m)?;
    home_rules::register(m)?;
    ear::register(m)?;
    ear_array::register(m)?;
    face::register(m)?;
    face_look::register(m)?;
    dialog::register(m)?;
    dialogue::register(m)?;
    transcript::register(m)?;
    expr::register(m)?;
    voice::register(m)?;
    rescue::register(m)?;
    rescue_ear::register(m)?;
    sentinel_memory::register(m)?;
    vault_media::register(m)?;
    matter::register(m)?;
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
    m.add_class::<ask_core::RustAskCore>()?;
    m.add_class::<gait_core::RustGaitCore>()?;
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
    m.add_function(wrap_pyfunction!(particles_extract_concept, m)?)?;
    m.add_function(wrap_pyfunction!(particles_synthesize_spec, m)?)?;
    m.add_function(wrap_pyfunction!(visual_route_select, m)?)?;
    m.add_function(wrap_pyfunction!(gaussian_splat_synthesize, m)?)?;
    m.add_function(wrap_pyfunction!(neural_radiance_synthesize, m)?)?;
    m.add_function(wrap_pyfunction!(depth_parallax_reconstruct, m)?)?;
    m.add_function(wrap_pyfunction!(visual_catalog_classify, m)?)?;
    m.add_function(wrap_pyfunction!(visual_agent_execute, m)?)?;
    m.add_function(wrap_pyfunction!(agents::agent_manifest_validate, m)?)?;
    m.add_class::<agents::RustAgentRegistry>()?;
    m.add_function(wrap_pyfunction!(agents::agent_layout_inspect, m)?)?;
    m.add_function(wrap_pyfunction!(agents::agent_scaffold, m)?)?;
    m.add_function(wrap_pyfunction!(agents::agent_genesis_decide, m)?)?;
    m.add_function(wrap_pyfunction!(forma::forma_compile, m)?)?;
    m.add_function(wrap_pyfunction!(forma::forma_sculpt, m)?)?;
    m.add_function(wrap_pyfunction!(forma::forma_schema, m)?)?;
    m.add_function(wrap_pyfunction!(forma::forma_anatomy_sculpt, m)?)?;
    m.add_function(wrap_pyfunction!(forma::forma_anatomy_preset, m)?)?;
    m.add_function(wrap_pyfunction!(forma::forma_anatomy_schema, m)?)?;
    m.add_class::<creations::RustCreationArchive>()?;
    m.add_function(wrap_pyfunction!(creations::creations_shard, m)?)?;
    m.add_function(wrap_pyfunction!(creations::creations_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(agents::agent_icon, m)?)?;
    ceo::register(m)?;
    dossier::register(m)?;
    vitals::register(m)?;
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
