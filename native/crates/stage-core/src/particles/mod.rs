pub mod codec;
pub mod hotspots;
pub mod lod;
pub mod sample;

pub use codec::{Cloud, HEADER, MAGIC, MIN_POINTS, ParticleError, decode, encode};
pub use hotspots::{Hotspot3D, extract_hotspots};
pub use lod::{LodLevel, ProgressiveAssembly, decompose_lod, sample_progressive_layer};
pub use sample::{Part, Shape, Spec, sample};

#[cfg(test)]
mod tests {
    use super::*;

    fn part(shape: Shape) -> Part {
        Part {
            shape,
            size: [1.0, 1.0, 1.0],
            at: [0.0, 0.0, 0.0],
            rot: [0.0, 0.0, 0.0],
            color: "#ff8800".to_owned(),
            weight: 1.0,
        }
    }

    #[test]
    fn sampling_is_deterministic_and_normalized() -> Result<(), ParticleError> {
        let spec = Spec {
            parts: vec![part(Shape::Sphere), part(Shape::Torus), part(Shape::Box)],
        };
        let a = sample(&spec, 3_000, 7)?;
        let b = sample(&spec, 3_000, 7)?;
        assert_eq!(a, b);
        assert_eq!(a.len(), 3_000);
        assert!(
            a.positions
                .iter()
                .flatten()
                .any(|v| v.unsigned_abs() == 32_767)
        );
        Ok(())
    }

    #[test]
    fn roundtrip_and_strict_decoding() -> Result<(), ParticleError> {
        let spec = Spec {
            parts: vec![part(Shape::Helix), part(Shape::Cone)],
        };
        let cloud = sample(&spec, 512, 1)?;
        let blob = encode(&cloud);
        assert_eq!(blob.len(), HEADER + 512 * 9);
        assert_eq!(decode(&blob)?, cloud);
        let mut bad = blob.clone();
        bad.push(0);
        assert!(decode(&bad).is_err());
        let mut magic = blob;
        if let Some(b) = magic.first_mut() {
            *b = b'X';
        }
        assert!(decode(&magic).is_err());
        Ok(())
    }

    #[test]
    fn progressive_lod_and_hotspots() -> Result<(), ParticleError> {
        let spec = Spec {
            parts: vec![
                part(Shape::Sphere),
                part(Shape::Torus),
                part(Shape::Cone),
                part(Shape::Helix),
            ],
        };
        let shell = sample_progressive_layer(&spec, LodLevel::BaseShell, 42)?;
        assert_eq!(shell.len(), 2_500);
        let full = sample_progressive_layer(&spec, LodLevel::FullUltra, 42)?;
        assert_eq!(full.len(), 24_000);

        let spots = extract_hotspots("cervello umano", &spec);
        assert_eq!(spots.len(), 4);
        assert_eq!(spots.first().map(|s| s.id.as_str()), Some("frontal_lobe"));
        Ok(())
    }
}
