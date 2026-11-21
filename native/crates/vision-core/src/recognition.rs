use std::collections::BTreeMap;

use zeroize::Zeroize;

pub const CHROMATIC_BINS: usize = 36;
pub const MAX_OBJECT_PROTOTYPES: usize = 512;
pub const MAX_ACTIVE_TRACKS: usize = 128;
pub const OBJECT_MATCH_THRESHOLD_BPS: u16 = 7_600;
pub const PERSON_REID_THRESHOLD_BPS: u16 = 7_400;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum SemanticColor {
    AchromaticBlack,
    AchromaticGrey,
    AchromaticWhite,
    WarmRed,
    WarmOrange,
    WarmYellow,
    NatureGreen,
    CoolCyan,
    CoolBlue,
    RoyalPurple,
    VibrantMagenta,
}

impl SemanticColor {
    #[must_use]
    pub const fn key(self) -> &'static str {
        match self {
            Self::AchromaticBlack => "color.black",
            Self::AchromaticGrey => "color.grey",
            Self::AchromaticWhite => "color.white",
            Self::WarmRed => "color.red",
            Self::WarmOrange => "color.orange",
            Self::WarmYellow => "color.yellow",
            Self::NatureGreen => "color.green",
            Self::CoolCyan => "color.cyan",
            Self::CoolBlue => "color.blue",
            Self::RoyalPurple => "color.purple",
            Self::VibrantMagenta => "color.magenta",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RgbSample {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ColorPaletteProfile {
    pub dominant: SemanticColor,
    pub secondary: Option<SemanticColor>,
    pub luminance_bps: u16,
    pub saturation_bps: u16,
    pub histogram_bps: [u16; 11],
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BoundingBox {
    pub x_min_bps: u16,
    pub y_min_bps: u16,
    pub x_max_bps: u16,
    pub y_max_bps: u16,
}

impl BoundingBox {
    #[must_use]
    pub fn iou_bps(self, other: Self) -> u16 {
        let inter_x1 = self.x_min_bps.max(other.x_min_bps);
        let inter_y1 = self.y_min_bps.max(other.y_min_bps);
        let inter_x2 = self.x_max_bps.min(other.x_max_bps);
        let inter_y2 = self.y_max_bps.min(other.y_max_bps);

        if inter_x2 <= inter_x1 || inter_y2 <= inter_y1 {
            return 0;
        }
        let inter_w = u64::from(inter_x2.saturating_sub(inter_x1));
        let inter_h = u64::from(inter_y2.saturating_sub(inter_y1));
        let inter_area = inter_w.saturating_mul(inter_h);

        let area_a = u64::from(self.x_max_bps.saturating_sub(self.x_min_bps))
            .saturating_mul(u64::from(self.y_max_bps.saturating_sub(self.y_min_bps)));
        let area_b = u64::from(other.x_max_bps.saturating_sub(other.x_min_bps))
            .saturating_mul(u64::from(other.y_max_bps.saturating_sub(other.y_min_bps)));
        let union_area = area_a.saturating_add(area_b).saturating_sub(inter_area);
        if union_area == 0 {
            return 0;
        }
        let ratio = inter_area
            .saturating_mul(10_000)
            .checked_div(union_area)
            .unwrap_or(0);
        u16::try_from(ratio.min(10_000)).unwrap_or(10_000)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct DetectedObject {
    pub track_id: u64,
    pub label_key: String,
    pub confidence_bps: u16,
    pub bbox: BoundingBox,
    pub palette: ColorPaletteProfile,
    pub learned_from_memory: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PersonVisualObservation {
    pub person_hint: Option<String>,
    pub face_embedding: Option<Vec<f32>>,
    pub face_quality_bps: u16,
    pub upper_garment_palette: ColorPaletteProfile,
    pub lower_garment_palette: ColorPaletteProfile,
    pub bbox: BoundingBox,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PersonIdentityMatch {
    pub person_id: String,
    pub combined_confidence_bps: u16,
    pub face_contribution_bps: u16,
    pub appearance_contribution_bps: u16,
    pub spatial_contribution_bps: u16,
    pub dominant_garment_color_key: &'static str,
}

#[derive(Debug)]
struct ObjectPrototype {
    label_key: String,
    embedding: Vec<f32>,
    dominant_color: SemanticColor,
    reinforcements: u32,
}

impl Drop for ObjectPrototype {
    fn drop(&mut self) {
        self.embedding.zeroize();
    }
}

#[derive(Debug)]
struct EnrolledPersonVisual {
    person_id: String,
    face_centroid: Vec<f32>,
    upper_color: SemanticColor,
    lower_color: SemanticColor,
    last_bbox: BoundingBox,
    last_seen_ms: u64,
}

impl Drop for EnrolledPersonVisual {
    fn drop(&mut self) {
        self.face_centroid.zeroize();
    }
}

#[derive(Debug, Default)]
pub struct VisualRecognitionEngine {
    objects: BTreeMap<String, ObjectPrototype>,
    people: BTreeMap<String, EnrolledPersonVisual>,
    next_track_id: u64,
}

#[must_use]
pub fn classify_rgb_pixel(sample: RgbSample) -> (SemanticColor, u16, u16) {
    let r = u32::from(sample.r);
    let g = u32::from(sample.g);
    let b = u32::from(sample.b);
    let max_c = r.max(g).max(b);
    let min_c = r.min(g).min(b);
    let delta = max_c.saturating_sub(min_c);

    let lum_bps =
        u16::try_from(max_c.saturating_mul(10_000).checked_div(255).unwrap_or(0)).unwrap_or(10_000);
    let sat_bps = if max_c == 0 {
        0
    } else {
        u16::try_from(delta.saturating_mul(10_000).checked_div(max_c).unwrap_or(0))
            .unwrap_or(10_000)
    };

    if lum_bps < 1_800 {
        return (SemanticColor::AchromaticBlack, lum_bps, sat_bps);
    }
    if sat_bps < 1_600 {
        if lum_bps > 7_800 {
            return (SemanticColor::AchromaticWhite, lum_bps, sat_bps);
        }
        return (SemanticColor::AchromaticGrey, lum_bps, sat_bps);
    }

    let hue_deg: i32 = if delta == 0 {
        0
    } else if max_c == r {
        let num = i32::from(sample.g)
            .saturating_sub(i32::from(sample.b))
            .saturating_mul(60);
        num.checked_div(i32::try_from(delta).unwrap_or(1))
            .unwrap_or(0)
            .rem_euclid(360)
    } else if max_c == g {
        let num = i32::from(sample.b)
            .saturating_sub(i32::from(sample.r))
            .saturating_mul(60);
        num.checked_div(i32::try_from(delta).unwrap_or(1))
            .unwrap_or(0)
            .saturating_add(120)
            .rem_euclid(360)
    } else {
        let num = i32::from(sample.r)
            .saturating_sub(i32::from(sample.g))
            .saturating_mul(60);
        num.checked_div(i32::try_from(delta).unwrap_or(1))
            .unwrap_or(0)
            .saturating_add(240)
            .rem_euclid(360)
    };

    let color = match hue_deg {
        0..=18 | 345..=360 => SemanticColor::WarmRed,
        19..=45 => SemanticColor::WarmOrange,
        46..=72 => SemanticColor::WarmYellow,
        73..=165 => SemanticColor::NatureGreen,
        166..=200 => SemanticColor::CoolCyan,
        201..=255 => SemanticColor::CoolBlue,
        256..=295 => SemanticColor::RoyalPurple,
        _ => SemanticColor::VibrantMagenta,
    };

    (color, lum_bps, sat_bps)
}

#[must_use]
pub fn extract_color_palette(samples: &[RgbSample]) -> ColorPaletteProfile {
    let all_colors = [
        SemanticColor::AchromaticBlack,
        SemanticColor::AchromaticGrey,
        SemanticColor::AchromaticWhite,
        SemanticColor::WarmRed,
        SemanticColor::WarmOrange,
        SemanticColor::WarmYellow,
        SemanticColor::NatureGreen,
        SemanticColor::CoolCyan,
        SemanticColor::CoolBlue,
        SemanticColor::RoyalPurple,
        SemanticColor::VibrantMagenta,
    ];
    let mut counts = [0_u32; 11];
    let mut lum_sum: u64 = 0;
    let mut sat_sum: u64 = 0;

    if samples.is_empty() {
        return ColorPaletteProfile {
            dominant: SemanticColor::AchromaticGrey,
            secondary: None,
            luminance_bps: 5_000,
            saturation_bps: 0,
            histogram_bps: [0; 11],
        };
    }

    for s in samples {
        let (col, lum, sat) = classify_rgb_pixel(*s);
        lum_sum = lum_sum.saturating_add(u64::from(lum));
        sat_sum = sat_sum.saturating_add(u64::from(sat));
        if let Some(pos) = all_colors.iter().position(|c| *c == col)
            && let Some(slot) = counts.get_mut(pos)
        {
            *slot = slot.saturating_add(1);
        }
    }

    let total = u64::try_from(samples.len()).unwrap_or(1).max(1);
    let mut histogram_bps = [0_u16; 11];
    let mut ranked: Vec<(u32, SemanticColor)> = Vec::with_capacity(11);

    for (idx, col) in all_colors.iter().enumerate() {
        let c = counts.get(idx).copied().unwrap_or(0);
        let bps = u16::try_from(
            u64::from(c)
                .saturating_mul(10_000)
                .checked_div(total)
                .unwrap_or(0),
        )
        .unwrap_or(0);
        if let Some(h) = histogram_bps.get_mut(idx) {
            *h = bps;
        }
        ranked.push((c, *col));
    }

    ranked.sort_by_key(|a| std::cmp::Reverse(a.0));
    let dominant = ranked
        .first()
        .map_or(SemanticColor::AchromaticGrey, |(_, c)| *c);
    let secondary = ranked.get(1).filter(|(c, _)| *c > 0).map(|(_, col)| *col);

    ColorPaletteProfile {
        dominant,
        secondary,
        luminance_bps: u16::try_from(lum_sum.checked_div(total).unwrap_or(5_000)).unwrap_or(5_000),
        saturation_bps: u16::try_from(sat_sum.checked_div(total).unwrap_or(0)).unwrap_or(0),
        histogram_bps,
    }
}

fn normalize_vec(v: &[f32]) -> Option<Vec<f32>> {
    if v.is_empty() || v.len() > 2048 || v.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm < 1e-9 {
        return None;
    }
    Some(v.iter().map(|x| x / norm).collect())
}

fn cosine_bps(a: &[f32], b: &[f32]) -> u16 {
    if a.len() != b.len() || a.is_empty() {
        return 0;
    }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let clamped = dot.clamp(0.0, 1.0);
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let bps = (clamped * 10_000.0).round() as u16;
    bps.min(10_000)
}

impl VisualRecognitionEngine {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn learn_object_prototype(
        &mut self,
        label_key: &str,
        embedding: &[f32],
        samples: &[RgbSample],
    ) -> bool {
        let clean = label_key.trim();
        if clean.is_empty() || clean.len() > 96 || clean.chars().any(char::is_control) {
            return false;
        }
        let Some(unit_emb) = normalize_vec(embedding) else {
            return false;
        };
        let palette = extract_color_palette(samples);

        if let Some(existing) = self.objects.get_mut(clean)
            && existing.embedding.len() == unit_emb.len()
        {
            for (dst, src) in existing.embedding.iter_mut().zip(unit_emb.iter()) {
                *dst = 0.8 * (*dst) + 0.2 * (*src);
            }
            if let Some(normed) = normalize_vec(&existing.embedding) {
                existing.embedding = normed;
            }
            existing.dominant_color = palette.dominant;
            existing.reinforcements = existing.reinforcements.saturating_add(1);
            return true;
        }

        if self.objects.len() >= MAX_OBJECT_PROTOTYPES
            && let Some(first_k) = self.objects.keys().next().cloned()
        {
            self.objects.remove(&first_k);
        }

        self.objects.insert(
            clean.to_owned(),
            ObjectPrototype {
                label_key: clean.to_owned(),
                embedding: unit_emb,
                dominant_color: palette.dominant,
                reinforcements: 1,
            },
        );
        true
    }

    pub fn recognize_object(
        &mut self,
        embedding: &[f32],
        samples: &[RgbSample],
        bbox: BoundingBox,
    ) -> Option<DetectedObject> {
        let unit_emb = normalize_vec(embedding)?;
        let palette = extract_color_palette(samples);

        let mut best_label = None;
        let mut best_score_bps: u16 = 0;

        for proto in self.objects.values() {
            let sim_bps = cosine_bps(&unit_emb, &proto.embedding);
            let color_bonus: u16 = if proto.dominant_color == palette.dominant {
                500
            } else {
                0
            };
            let total = sim_bps.saturating_add(color_bonus).min(10_000);
            if total > best_score_bps {
                best_score_bps = total;
                best_label = Some(proto.label_key.clone());
            }
        }

        let label_key = best_label?;
        if best_score_bps < OBJECT_MATCH_THRESHOLD_BPS {
            return None;
        }

        self.next_track_id = self.next_track_id.saturating_add(1);
        Some(DetectedObject {
            track_id: self.next_track_id,
            label_key,
            confidence_bps: best_score_bps,
            bbox,
            palette,
            learned_from_memory: true,
        })
    }

    pub fn enroll_or_update_person(
        &mut self,
        person_id: &str,
        obs: &PersonVisualObservation,
    ) -> bool {
        let clean = person_id.trim();
        if clean.is_empty() || clean.len() > 80 || clean.chars().any(char::is_control) {
            return false;
        }
        let Some(raw_face) = &obs.face_embedding else {
            return false;
        };
        let Some(unit_face) = normalize_vec(raw_face) else {
            return false;
        };

        if let Some(entry) = self.people.get_mut(clean)
            && entry.face_centroid.len() == unit_face.len()
        {
            for (dst, src) in entry.face_centroid.iter_mut().zip(unit_face.iter()) {
                *dst = 0.85 * (*dst) + 0.15 * (*src);
            }
            if let Some(normed) = normalize_vec(&entry.face_centroid) {
                entry.face_centroid = normed;
            }
            entry.upper_color = obs.upper_garment_palette.dominant;
            entry.lower_color = obs.lower_garment_palette.dominant;
            entry.last_bbox = obs.bbox;
            entry.last_seen_ms = obs.at_ms;
            return true;
        }

        self.people.insert(
            clean.to_owned(),
            EnrolledPersonVisual {
                person_id: clean.to_owned(),
                face_centroid: unit_face,
                upper_color: obs.upper_garment_palette.dominant,
                lower_color: obs.lower_garment_palette.dominant,
                last_bbox: obs.bbox,
                last_seen_ms: obs.at_ms,
            },
        );
        true
    }

    #[must_use]
    pub fn identify_person(&self, obs: &PersonVisualObservation) -> Option<PersonIdentityMatch> {
        let unit_face = obs.face_embedding.as_deref().and_then(normalize_vec);
        let mut best_match: Option<PersonIdentityMatch> = None;

        for enrolled in self.people.values() {
            let face_bps = match &unit_face {
                Some(uf) if obs.face_quality_bps >= 3_500 => {
                    cosine_bps(uf, &enrolled.face_centroid)
                }
                _ => 0,
            };

            let mut appearance_bps: u16 = 0;
            if enrolled.upper_color == obs.upper_garment_palette.dominant {
                appearance_bps = appearance_bps.saturating_add(5_500);
            }
            if enrolled.lower_color == obs.lower_garment_palette.dominant {
                appearance_bps = appearance_bps.saturating_add(4_500);
            }

            let dt_ms = obs.at_ms.saturating_sub(enrolled.last_seen_ms);
            let spatial_bps = if dt_ms <= 15_000 {
                obs.bbox.iou_bps(enrolled.last_bbox)
            } else {
                0
            };

            let combined_bps = if face_bps >= 7_800 {
                let weighted = u32::from(face_bps)
                    .saturating_mul(75)
                    .saturating_add(u32::from(appearance_bps).saturating_mul(15))
                    .saturating_add(u32::from(spatial_bps).saturating_mul(10))
                    .checked_div(100)
                    .unwrap_or(0);
                u16::try_from(weighted.min(10_000)).unwrap_or(10_000)
            } else {
                let weighted = u32::from(face_bps)
                    .saturating_mul(35)
                    .saturating_add(u32::from(appearance_bps).saturating_mul(45))
                    .saturating_add(u32::from(spatial_bps).saturating_mul(20))
                    .checked_div(100)
                    .unwrap_or(0);
                u16::try_from(weighted.min(10_000)).unwrap_or(10_000)
            };

            if combined_bps >= PERSON_REID_THRESHOLD_BPS
                && best_match
                    .as_ref()
                    .is_none_or(|m| combined_bps > m.combined_confidence_bps)
            {
                best_match = Some(PersonIdentityMatch {
                    person_id: enrolled.person_id.clone(),
                    combined_confidence_bps: combined_bps,
                    face_contribution_bps: face_bps,
                    appearance_contribution_bps: appearance_bps,
                    spatial_contribution_bps: spatial_bps,
                    dominant_garment_color_key: obs.upper_garment_palette.dominant.key(),
                });
            }
        }

        best_match
    }
}
