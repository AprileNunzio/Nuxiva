use crate::gesture::{Direction, GestureKind};
use crate::landmarks::Handedness;
use crate::pose::Pose;
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PointerPhase {
    Move,
    Down,
    Drag,
    Up,
    Hidden,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum DuoPhase {
    Start,
    Update,
    End,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum GestureEvent {
    Pointer {
        phase: PointerPhase,
        x: f32,
        y: f32,
        pinch: bool,
        flick: Option<Direction>,
    },
    Gesture {
        gesture: GestureKind,
        hand: Handedness,
        confidence: f32,
        modifier: Option<Pose>,
    },
    Duo {
        phase: DuoPhase,
        x: f32,
        y: f32,
        scale: f32,
        rotate: f32,
        pan_x: f32,
        pan_y: f32,
    },
    Action {
        action: String,
        args: BTreeMap<String, String>,
        gesture: GestureKind,
        hand: Handedness,
        confirm: bool,
    },
}
