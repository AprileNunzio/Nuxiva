#![forbid(unsafe_code)]

pub mod cache;
pub mod depth_parallax;
pub mod director;
pub mod gaussian_splat;
pub mod morphogenesis;
pub mod neural_radiance;
pub mod particles;
pub mod visual_router;

pub use cache::BlobCache;
pub use depth_parallax::{DepthParallaxScene, DepthReliefVertex, reconstruct_depth_relief};
pub use director::{
    Context, PlanRequest, PlanResponse, Planned, Previous, State, SurfaceSpec, plan,
};
pub use gaussian_splat::{GaussianScene, GaussianSplat3D, synthesize_gaussian_scene};
pub use morphogenesis::{extract_visual_concept, synthesize_sculpture};
pub use neural_radiance::{NeuralRadianceScene, SdfNode, synthesize_radiance_scene};
pub use particles::{
    Cloud, Hotspot3D, LodLevel, Part, ParticleError, ProgressiveAssembly, Shape, Spec, decode,
    decompose_lod, encode, extract_hotspots, sample, sample_progressive_layer,
};
pub use visual_router::{VisualEngineKind, VisualRouteDecision, select_visual_engine};
