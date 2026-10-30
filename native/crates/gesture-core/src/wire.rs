use crate::error::GestureError;
use crate::events::GestureEvent;
use crate::landmarks::{Frame, Hand, Handedness, Point};
use serde::Deserialize;

pub const MAX_FRAME_JSON: usize = 32_768;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct HandWire {
    #[serde(default)]
    handedness: Handedness,
    #[serde(default = "full_score")]
    score: f32,
    points: Vec<[f32; 3]>,
}

const fn full_score() -> f32 {
    1.0
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct FrameWire {
    t: u64,
    #[serde(default)]
    hands: Vec<HandWire>,
}

pub fn frame_from_json(raw: &str) -> Result<Frame, GestureError> {
    if raw.len() > MAX_FRAME_JSON {
        return Err(GestureError::FrameTooLarge);
    }
    let wire: FrameWire =
        serde_json::from_str(raw).map_err(|e| GestureError::FrameInvalid(e.to_string()))?;
    let hands = wire
        .hands
        .into_iter()
        .map(|h| {
            let points: Vec<Point> = h
                .points
                .iter()
                .map(|[x, y, z]| Point {
                    x: *x,
                    y: *y,
                    z: *z,
                })
                .collect();
            Hand::new(&points, h.handedness, h.score)
        })
        .collect::<Result<Vec<_>, _>>()?;
    Frame::new(wire.t, hands)
}

pub fn events_to_json(events: &[GestureEvent]) -> Result<String, GestureError> {
    serde_json::to_string(events).map_err(|e| GestureError::ProfileInvalid(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_frame() -> Result<(), GestureError> {
        let points = vec![[0.5_f32, 0.5, 0.0]; 21];
        let raw = serde_json::json!({"t": 10, "hands": [{"handedness": "left", "points": points}]})
            .to_string();
        let frame = frame_from_json(&raw)?;
        assert_eq!(frame.hands.len(), 1);
        assert_eq!(
            frame.hands.first().map(|h| h.handedness),
            Some(Handedness::Left)
        );
        Ok(())
    }

    #[test]
    fn rejects_malformed() {
        assert!(frame_from_json(r#"{"t":1,"hands":[{"points":[[0,0,0]]}]}"#).is_err());
        assert!(frame_from_json(r#"{"t":1,"extra":true}"#).is_err());
        assert!(frame_from_json(&" ".repeat(MAX_FRAME_JSON + 1)).is_err());
    }
}
