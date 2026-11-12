#![forbid(unsafe_code)]

pub mod agent_catalog;
pub mod cache;
pub mod depth_parallax;
pub mod diorama;
pub mod director;
pub mod gaussian_splat;
pub mod morphogenesis;
pub mod neural_radiance;
pub mod particles;
pub mod visual_catalog;
pub mod visual_router;

pub use agent_catalog::{AgentDatabase, FastAgentManifest};
pub use cache::BlobCache;
pub use depth_parallax::{
    DepthParallaxAgentArtifact, DepthParallaxScene, DepthReliefVertex,
    execute_depth_parallax_agent, reconstruct_depth_relief,
};
pub use diorama::{DioramaAgentArtifact, DioramaAtmosphere, DioramaLayer3D, execute_diorama_agent};
pub use director::{
    Context, PlanRequest, PlanResponse, Planned, Previous, State, SurfaceSpec, plan,
};
pub use gaussian_splat::{
    GaussianAgentArtifact, GaussianScene, GaussianSplat3D, execute_gaussian_agent,
    synthesize_gaussian_scene,
};
pub use morphogenesis::{extract_visual_concept, synthesize_sculpture};
pub use neural_radiance::{
    NeuralRadianceAgentArtifact, NeuralRadianceScene, SdfNode, execute_neural_radiance_agent,
    synthesize_radiance_scene,
};
pub use particles::{
    Cloud, Hotspot3D, LodLevel, Part, ParticleAgentArtifact, ParticleAgentSkill,
    ParticleCritiqueReport, ParticleError, ProgressiveAssembly, Shape, Spec, decode, decompose_lod,
    encode, execute_particle_agent, extract_hotspots, particle_agent_skills, sample,
    sample_progressive_layer,
};
pub use visual_catalog::{
    AcademicLectureCard, CatalogEntry, CatalogIndex, classify_academic_entry, map_engine_folder,
};
pub use visual_router::{VisualEngineKind, VisualRouteDecision, select_visual_engine};
