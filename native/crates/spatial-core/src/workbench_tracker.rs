use serde::{Deserialize, Serialize};

pub type BoundingBox = [f64; 4];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Detection {
    pub label: String,
    pub bbox: BoundingBox,
    #[serde(default)]
    pub score: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrackedComponent {
    pub track_id: u32,
    pub label: String,
    pub bbox: BoundingBox,
    pub score: f64,
    pub hits: u32,
    pub missed: u32,
}

#[derive(Debug, Clone)]
pub struct ComponentTracker {
    tracks: Vec<TrackedComponent>,
    next_id: u32,
    iou_threshold: f64,
    smoothing: f64,
    max_missed: u32,
}

impl ComponentTracker {
    #[must_use]
    pub fn new(iou_threshold: f64, smoothing: f64, max_missed: u32) -> Self {
        Self {
            tracks: Vec::new(),
            next_id: 1,
            iou_threshold: iou_threshold.clamp(0.0, 1.0),
            smoothing: smoothing.clamp(0.01, 1.0),
            max_missed,
        }
    }

    pub fn update(&mut self, detections: &[Detection]) -> &[TrackedComponent] {
        let mut claimed: Vec<usize> = Vec::new();
        let mut unmatched: Vec<&Detection> = Vec::new();
        for detection in detections {
            let normalized = normalize_box(detection.bbox);
            match self.best_track(detection, normalized, &claimed) {
                Some(index) => {
                    claimed.push(index);
                    let smoothing = self.smoothing;
                    if let Some(track) = self.tracks.get_mut(index) {
                        track.bbox = blend(track.bbox, normalized, smoothing);
                        track.score = detection.score;
                        track.hits = track.hits.saturating_add(1);
                        track.missed = 0;
                    }
                }
                None => unmatched.push(detection),
            }
        }
        for (index, track) in self.tracks.iter_mut().enumerate() {
            if !claimed.contains(&index) {
                track.missed = track.missed.saturating_add(1);
            }
        }
        let max_missed = self.max_missed;
        self.tracks.retain(|track| track.missed <= max_missed);
        for detection in unmatched {
            let track_id = self.next_id;
            self.next_id = self.next_id.saturating_add(1);
            self.tracks.push(TrackedComponent {
                track_id,
                label: detection.label.clone(),
                bbox: normalize_box(detection.bbox),
                score: detection.score,
                hits: 1,
                missed: 0,
            });
        }
        &self.tracks
    }

    #[must_use]
    pub fn tracks(&self) -> &[TrackedComponent] {
        &self.tracks
    }

    pub fn relabel(&mut self, track_id: u32, label: &str) -> bool {
        match self.tracks.iter_mut().find(|t| t.track_id == track_id) {
            Some(track) => {
                label.clone_into(&mut track.label);
                true
            }
            None => false,
        }
    }

    pub fn reset(&mut self) {
        self.tracks.clear();
        self.next_id = 1;
    }

    fn best_track(
        &self,
        detection: &Detection,
        normalized: BoundingBox,
        claimed: &[usize],
    ) -> Option<usize> {
        let mut best: Option<(usize, f64)> = None;
        for (index, track) in self.tracks.iter().enumerate() {
            if claimed.contains(&index) || track.label != detection.label {
                continue;
            }
            let overlap = iou(track.bbox, normalized);
            if overlap < self.iou_threshold {
                continue;
            }
            if best.is_none_or(|(_, current)| overlap > current) {
                best = Some((index, overlap));
            }
        }
        best.map(|(index, _)| index)
    }
}

impl Default for ComponentTracker {
    fn default() -> Self {
        Self::new(0.3, 0.4, 5)
    }
}

#[must_use]
pub fn normalize_box(bbox: BoundingBox) -> BoundingBox {
    let [x1, y1, x2, y2] = bbox.map(|v| {
        if v.is_finite() {
            v.clamp(0.0, 1.0)
        } else {
            0.0
        }
    });
    [x1.min(x2), y1.min(y2), x1.max(x2), y1.max(y2)]
}

#[must_use]
pub fn iou(left: BoundingBox, right: BoundingBox) -> f64 {
    let [lx1, ly1, lx2, ly2] = left;
    let [rx1, ry1, rx2, ry2] = right;
    let width = (lx2.min(rx2) - lx1.max(rx1)).max(0.0);
    let height = (ly2.min(ry2) - ly1.max(ry1)).max(0.0);
    let intersection = width * height;
    let union = (lx2 - lx1) * (ly2 - ly1) + (rx2 - rx1) * (ry2 - ry1) - intersection;
    if union <= f64::EPSILON {
        0.0
    } else {
        intersection / union
    }
}

fn blend(old: BoundingBox, new: BoundingBox, alpha: f64) -> BoundingBox {
    let [ox1, oy1, ox2, oy2] = old;
    let [nx1, ny1, nx2, ny2] = new;
    [
        ox1 + alpha * (nx1 - ox1),
        oy1 + alpha * (ny1 - oy1),
        ox2 + alpha * (nx2 - ox2),
        oy2 + alpha * (ny2 - oy2),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn detection(label: &str, bbox: BoundingBox) -> Detection {
        Detection {
            label: label.to_owned(),
            bbox,
            score: 0.9,
        }
    }

    #[test]
    fn iou_of_identical_boxes_is_one() {
        let value = iou([0.1, 0.1, 0.5, 0.5], [0.1, 0.1, 0.5, 0.5]);
        assert!((value - 1.0).abs() < 1e-9);
    }

    #[test]
    fn iou_of_disjoint_boxes_is_zero() {
        assert!(iou([0.0, 0.0, 0.1, 0.1], [0.5, 0.5, 0.9, 0.9]).abs() < 1e-9);
    }

    #[test]
    fn track_identity_is_stable_and_smoothed() {
        let mut tracker = ComponentTracker::new(0.3, 0.5, 2);
        tracker.update(&[detection("U1", [0.20, 0.20, 0.40, 0.40])]);
        let tracks = tracker.update(&[detection("U1", [0.22, 0.20, 0.42, 0.40])]);
        assert_eq!(tracks.len(), 1);
        let first = tracks.first().map(|t| (t.track_id, t.hits, t.bbox));
        let (id, hits, bbox) = first.unwrap_or((0, 0, [0.0; 4]));
        assert_eq!((id, hits), (1, 2));
        assert!(bbox[0] > 0.20 && bbox[0] < 0.22);
    }

    #[test]
    fn lost_tracks_expire() {
        let mut tracker = ComponentTracker::new(0.3, 0.5, 1);
        tracker.update(&[detection("C1", [0.1, 0.1, 0.2, 0.2])]);
        tracker.update(&[]);
        assert_eq!(tracker.tracks().len(), 1);
        tracker.update(&[]);
        assert!(tracker.tracks().is_empty());
    }

    #[test]
    fn relabel_changes_label() {
        let mut tracker = ComponentTracker::default();
        tracker.update(&[detection("X", [0.1, 0.1, 0.3, 0.3])]);
        assert!(tracker.relabel(1, "TIP41C"));
        assert!(!tracker.relabel(99, "none"));
        assert_eq!(
            tracker.tracks().first().map(|t| t.label.as_str()),
            Some("TIP41C")
        );
    }
}
