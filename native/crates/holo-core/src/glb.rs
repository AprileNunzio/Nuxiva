use serde::Serialize;
use serde_json::Value;

use crate::error::{HoloError, HoloResult};

pub const MAX_GLB: usize = 96 * 1024 * 1024;
const MAX_JSON: usize = 16 * 1024 * 1024;
const MAGIC: &[u8; 4] = b"glTF";
const JSON_CHUNK: u32 = 0x4E4F_534A;
const SUPPORTED: [&str; 8] = [
    "KHR_materials_clearcoat",
    "KHR_materials_transmission",
    "KHR_materials_ior",
    "KHR_materials_specular",
    "KHR_materials_sheen",
    "KHR_materials_emissive_strength",
    "KHR_texture_transform",
    "KHR_materials_unlit",
];

#[derive(Debug, Clone, Default, PartialEq, Serialize)]
pub struct Report {
    pub bytes: usize,
    pub meshes: usize,
    pub primitives: usize,
    pub triangles: u64,
    pub materials: usize,
    pub pbr_materials: usize,
    pub textures: usize,
    pub normal_maps: usize,
    pub animations: usize,
    pub skins: usize,
    pub extent: [f32; 3],
    pub background_suspect: bool,
    pub external_uris: usize,
    pub unsupported: Vec<String>,
    pub score: u8,
    pub reasons: Vec<&'static str>,
}

fn u32_at(bytes: &[u8], at: usize) -> Option<u32> {
    let end = at.checked_add(4)?;
    let slice = bytes.get(at..end)?;
    let arr: [u8; 4] = slice.try_into().ok()?;
    Some(u32::from_le_bytes(arr))
}

fn json_chunk(bytes: &[u8]) -> HoloResult<Value> {
    if bytes.len() > MAX_GLB {
        return Err(HoloError::TooLarge);
    }
    if bytes.get(0..4) != Some(MAGIC.as_slice()) || u32_at(bytes, 4) != Some(2) {
        return Err(HoloError::BadModel);
    }
    let declared = usize::try_from(u32_at(bytes, 8).ok_or(HoloError::BadModel)?)
        .map_err(|_| HoloError::BadModel)?;
    if declared != bytes.len() {
        return Err(HoloError::BadModel);
    }
    let length = usize::try_from(u32_at(bytes, 12).ok_or(HoloError::BadModel)?)
        .map_err(|_| HoloError::BadModel)?;
    if u32_at(bytes, 16) != Some(JSON_CHUNK) || length > MAX_JSON {
        return Err(HoloError::BadModel);
    }
    let end = 20_usize.checked_add(length).ok_or(HoloError::BadModel)?;
    let raw = bytes.get(20..end).ok_or(HoloError::BadModel)?;
    serde_json::from_slice(raw).map_err(|_| HoloError::BadModel)
}

fn list<'a>(root: &'a Value, key: &str) -> &'a [Value] {
    root.get(key)
        .and_then(Value::as_array)
        .map_or(&[], Vec::as_slice)
}

fn count_of(value: &Value) -> u64 {
    value.get("count").and_then(Value::as_u64).unwrap_or(0)
}

fn triangles(root: &Value, primitive: &Value) -> u64 {
    let accessors = list(root, "accessors");
    let lookup = |index: Option<u64>| {
        index
            .and_then(|i| usize::try_from(i).ok())
            .and_then(|i| accessors.get(i))
            .map_or(0, count_of)
    };
    let mode = primitive.get("mode").and_then(Value::as_u64).unwrap_or(4);
    if mode != 4 {
        return 0;
    }
    let indices = lookup(primitive.get("indices").and_then(Value::as_u64));
    let vertices = lookup(
        primitive
            .get("attributes")
            .and_then(|a| a.get("POSITION"))
            .and_then(Value::as_u64),
    );
    if indices > 0 {
        indices / 3
    } else {
        vertices / 3
    }
}

#[allow(clippy::cast_possible_truncation)]
fn bounds(root: &Value, primitive: &Value) -> Option<[f32; 3]> {
    let index = primitive
        .get("attributes")?
        .get("POSITION")?
        .as_u64()
        .and_then(|i| usize::try_from(i).ok())?;
    let accessor = list(root, "accessors").get(index)?;
    let lo = accessor.get("min")?.as_array()?;
    let hi = accessor.get("max")?.as_array()?;
    let mut out = [0.0_f32; 3];
    for ((slot, l), h) in out.iter_mut().zip(lo).zip(hi) {
        let span = h.as_f64()? - l.as_f64()?;
        *slot = if span.is_finite() {
            span.abs() as f32
        } else {
            0.0
        };
    }
    Some(out)
}

fn external(root: &Value) -> usize {
    ["buffers", "images"]
        .iter()
        .flat_map(|key| list(root, key))
        .filter(|item| item.get("uri").and_then(Value::as_str).is_some())
        .count()
}

pub fn inspect(bytes: &[u8]) -> HoloResult<Report> {
    let root = json_chunk(bytes)?;
    let mut report = Report {
        bytes: bytes.len(),
        meshes: list(&root, "meshes").len(),
        materials: list(&root, "materials").len(),
        textures: list(&root, "textures").len(),
        animations: list(&root, "animations").len(),
        skins: list(&root, "skins").len(),
        external_uris: external(&root),
        ..Report::default()
    };
    report.unsupported = list(&root, "extensionsRequired")
        .iter()
        .filter_map(Value::as_str)
        .filter(|name| !SUPPORTED.contains(name))
        .map(str::to_owned)
        .collect();
    for material in list(&root, "materials") {
        let pbr = material.get("pbrMetallicRoughness");
        if pbr.is_some_and(|p| p.get("baseColorTexture").is_some()) {
            report.pbr_materials = report.pbr_materials.saturating_add(1);
        }
        if material.get("normalTexture").is_some() {
            report.normal_maps = report.normal_maps.saturating_add(1);
        }
    }
    let mut spans: Vec<f32> = Vec::new();
    let mut extent = [0.0_f32; 3];
    for mesh in list(&root, "meshes") {
        for primitive in list(mesh, "primitives") {
            report.primitives = report.primitives.saturating_add(1);
            report.triangles = report.triangles.saturating_add(triangles(&root, primitive));
            if let Some(b) = bounds(&root, primitive) {
                spans.push(b.iter().copied().fold(0.0, f32::max));
                for (e, v) in extent.iter_mut().zip(b) {
                    *e = e.max(v);
                }
            }
        }
    }
    report.extent = extent;
    report.background_suspect = background(&mut spans);
    score(&mut report);
    Ok(report)
}

fn background(spans: &mut [f32]) -> bool {
    if spans.len() < 3 {
        return false;
    }
    spans.sort_by(f32::total_cmp);
    let middle = spans.len() / 2;
    let median = spans.get(middle).copied().unwrap_or(0.0);
    let largest = spans.last().copied().unwrap_or(0.0);
    median > 0.0 && largest > median * 25.0
}

fn score(report: &mut Report) {
    let mut points: u32 = 0;
    let mut reasons = Vec::new();
    points = points.saturating_add(match report.triangles {
        0..=1_999 => {
            reasons.push("low_poly");
            5
        }
        2_000..=19_999 => 18,
        20_000..=1_500_000 => 30,
        _ => {
            reasons.push("too_heavy");
            12
        }
    });
    if report.pbr_materials > 0 {
        points = points.saturating_add(20);
    } else {
        reasons.push("no_textures");
    }
    if report.normal_maps > 0 {
        points = points.saturating_add(10);
    }
    if report.animations > 0 {
        points = points.saturating_add(20);
    } else {
        reasons.push("static");
    }
    if report.background_suspect {
        reasons.push("background");
    } else {
        points = points.saturating_add(20);
    }
    if report.external_uris > 0 || !report.unsupported.is_empty() || report.meshes == 0 {
        reasons.push("unusable");
        points = 0;
    }
    report.score = u8::try_from(points.min(100)).unwrap_or(100);
    report.reasons = reasons;
}

pub fn inspect_json(bytes: &[u8]) -> HoloResult<String> {
    serde_json::to_string(&inspect(bytes)?).map_err(|_| HoloError::BadJson)
}
