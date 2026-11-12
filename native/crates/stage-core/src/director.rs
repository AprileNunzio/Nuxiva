use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const SHOWN_AT: f64 = 50.0;
pub const MIN_AT: f64 = 20.0;
pub const MARGIN: f64 = 6.0;
pub const WEIGHT_LIMIT: f64 = 40.0;
pub const MAX_SURFACES: usize = 128;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum State {
    Shown,
    Min,
    Hidden,
}

#[allow(clippy::struct_excessive_bools)]
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Context {
    pub mode: String,
    pub listening: bool,
    pub conversing: bool,
    pub typing: bool,
    pub speaking: bool,
    pub people: u32,
    pub desk: Vec<String>,
    pub music: bool,
    pub project: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceSpec {
    pub id: String,
    #[serde(default)]
    pub priority: f64,
    #[serde(default)]
    pub group: Option<String>,
    #[serde(default)]
    pub dwell_ms: u64,
    #[serde(default)]
    pub pinned: bool,
    #[serde(default = "enabled_default")]
    pub enabled: bool,
}

const fn enabled_default() -> bool {
    true
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Previous {
    pub state: State,
    pub since_ms: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct PlanRequest {
    pub now_ms: u64,
    pub context: Context,
    pub surfaces: Vec<SurfaceSpec>,
    pub previous: BTreeMap<String, Previous>,
    pub weights: BTreeMap<String, BTreeMap<String, f64>>,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Planned {
    pub state: State,
    pub score: f64,
    pub since_ms: u64,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct PlanResponse {
    pub context_key: String,
    pub surfaces: BTreeMap<String, Planned>,
}

#[must_use]
pub fn context_key(ctx: &Context) -> String {
    if !ctx.mode.is_empty() && ctx.mode != "face" {
        return ctx.mode.clone();
    }
    if ctx.typing {
        "typing".to_owned()
    } else if ctx.conversing || ctx.listening || ctx.speaking {
        "voice".to_owned()
    } else if ctx.people == 0 {
        "empty".to_owned()
    } else {
        "idle".to_owned()
    }
}

fn has(ctx: &Context, widget: &str) -> bool {
    ctx.desk.iter().any(|w| w == widget)
}

fn adjust(id: &str, ctx: &Context, key: &str) -> (f64, Option<State>) {
    let voice = key == "voice";
    let face = ctx.mode.is_empty() || ctx.mode == "face";
    let ambient = matches!(
        id,
        "rail_voice"
            | "rail_home"
            | "rail_scan"
            | "rail_vitals"
            | "rail_learned"
            | "project"
            | "music_clock"
            | "brain_badge"
            | "thinking"
    );
    if !face && ambient {
        return (0.0, Some(State::Hidden));
    }
    match id {
        "chat" if ctx.typing => (0.0, Some(State::Shown)),
        "chat" if voice => (-30.0, None),
        "chat" if key == "empty" => (-10.0, None),
        "thinking" if ctx.typing => (-40.0, None),
        "rail_scan" | "rail_vitals" | "rail_learned" if ctx.people == 0 => {
            (0.0, Some(State::Hidden))
        }
        "rail_scan" if voice => (-5.0, None),
        "rail_vitals" | "rail_learned" if voice => (-35.0, None),
        "project" if !ctx.project => (0.0, Some(State::Hidden)),
        "project" if has(ctx, "project_status") => (0.0, Some(State::Hidden)),
        "rail_home" | "project" if voice => (-10.0, None),
        "music_clock" if !ctx.music || has(ctx, "music") => (0.0, Some(State::Hidden)),
        "brain_badge" if voice => (-20.0, None),
        _ => (0.0, None),
    }
}

fn band(score: f64) -> State {
    if score >= SHOWN_AT {
        State::Shown
    } else if score >= MIN_AT {
        State::Min
    } else {
        State::Hidden
    }
}

fn rank(state: State) -> u8 {
    match state {
        State::Shown => 2,
        State::Min => 1,
        State::Hidden => 0,
    }
}

fn settle(score: f64, target: State, prev: Option<&Previous>, dwell_ms: u64, now_ms: u64) -> State {
    let Some(prev) = prev else {
        return target;
    };
    if prev.state == target {
        return target;
    }
    if now_ms.saturating_sub(prev.since_ms) < dwell_ms {
        return prev.state;
    }
    let boundary = if rank(target) > rank(prev.state) {
        let edge = if rank(prev.state) == 0 {
            MIN_AT
        } else {
            SHOWN_AT
        };
        score >= edge + MARGIN
    } else {
        let edge = if rank(prev.state) == 2 {
            SHOWN_AT
        } else {
            MIN_AT
        };
        score < edge - MARGIN
    };
    if boundary { target } else { prev.state }
}

#[must_use]
pub fn plan(req: &PlanRequest) -> PlanResponse {
    let key = context_key(&req.context);
    let mut out: BTreeMap<String, Planned> = BTreeMap::new();
    for spec in req.surfaces.iter().take(MAX_SURFACES) {
        let prev = req.previous.get(&spec.id);
        let weight = req
            .weights
            .get(&spec.id)
            .and_then(|w| w.get(&key))
            .copied()
            .filter(|w| w.is_finite())
            .map_or(0.0, |w| w.clamp(-WEIGHT_LIMIT, WEIGHT_LIMIT));
        let base = if spec.priority.is_finite() {
            spec.priority
        } else {
            0.0
        };
        let (delta, hard) = if spec.pinned {
            (0.0, Some(State::Shown))
        } else if !spec.enabled {
            (0.0, Some(State::Hidden))
        } else {
            adjust(&spec.id, &req.context, &key)
        };
        let score = (base + delta + weight).clamp(0.0, 100.0);
        let state =
            hard.unwrap_or_else(|| settle(score, band(score), prev, spec.dwell_ms, req.now_ms));
        let since_ms = match prev {
            Some(p) if p.state == state => p.since_ms,
            _ => req.now_ms,
        };
        out.insert(
            spec.id.clone(),
            Planned {
                state,
                score,
                since_ms,
            },
        );
    }
    let mut groups: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for spec in req.surfaces.iter().take(MAX_SURFACES) {
        if let Some(group) = spec.group.as_deref() {
            groups.entry(group).or_default().push(spec.id.as_str());
        }
    }
    for members in groups.values() {
        let winner = members
            .iter()
            .filter_map(|id| out.get(*id).map(|p| (*id, *p)))
            .filter(|(_, p)| p.state != State::Hidden)
            .max_by(|a, b| a.1.score.total_cmp(&b.1.score).then_with(|| b.0.cmp(a.0)))
            .map(|(id, _)| id);
        for id in members {
            if Some(*id) == winner {
                continue;
            }
            if let Some(p) = out.get_mut(*id) {
                if p.state != State::Hidden {
                    p.state = State::Hidden;
                    p.since_ms = req.now_ms;
                }
            }
        }
    }
    PlanResponse {
        context_key: key,
        surfaces: out,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn surface(id: &str, priority: f64, group: Option<&str>) -> SurfaceSpec {
        SurfaceSpec {
            id: id.to_owned(),
            priority,
            group: group.map(str::to_owned),
            dwell_ms: 0,
            pinned: false,
            enabled: true,
        }
    }

    fn state_of(res: &PlanResponse, id: &str) -> Option<State> {
        res.surfaces.get(id).map(|p| p.state)
    }

    #[test]
    fn chat_minimizes_while_talking_and_returns_when_typing() {
        let mut req = PlanRequest {
            now_ms: 10_000,
            surfaces: vec![surface("chat", 60.0, None)],
            ..PlanRequest::default()
        };
        req.context.people = 1;
        req.context.conversing = true;
        assert_eq!(state_of(&plan(&req), "chat"), Some(State::Min));
        req.context.typing = true;
        assert_eq!(state_of(&plan(&req), "chat"), Some(State::Shown));
    }

    #[test]
    fn duplicates_keep_only_the_strongest() {
        let mut mic = surface("mic", 100.0, Some("listening"));
        mic.pinned = true;
        let req = PlanRequest {
            now_ms: 1,
            surfaces: vec![
                mic,
                surface("rail_voice", 30.0, Some("listening")),
                surface("w:listening", 70.0, Some("listening")),
            ],
            ..PlanRequest::default()
        };
        let res = plan(&req);
        assert_eq!(state_of(&res, "mic"), Some(State::Shown));
        assert_eq!(state_of(&res, "w:listening"), Some(State::Hidden));
        assert_eq!(state_of(&res, "rail_voice"), Some(State::Hidden));
    }

    #[test]
    fn hysteresis_and_dwell_prevent_flicker() {
        let mut spec = surface("brain_badge", 52.0, None);
        spec.dwell_ms = 5_000;
        let mut req = PlanRequest {
            now_ms: 1_000,
            surfaces: vec![spec],
            ..PlanRequest::default()
        };
        req.context.people = 1;
        req.previous.insert(
            "brain_badge".to_owned(),
            Previous {
                state: State::Min,
                since_ms: 0,
            },
        );
        assert_eq!(state_of(&plan(&req), "brain_badge"), Some(State::Min));
        req.now_ms = 9_000;
        assert_eq!(state_of(&plan(&req), "brain_badge"), Some(State::Min));
        req.weights
            .entry("brain_badge".to_owned())
            .or_default()
            .insert("idle".to_owned(), 10.0);
        assert_eq!(state_of(&plan(&req), "brain_badge"), Some(State::Shown));
    }

    #[test]
    fn learned_weights_are_bounded() {
        let mut req = PlanRequest {
            now_ms: 1,
            surfaces: vec![surface("rail_home", 60.0, None)],
            ..PlanRequest::default()
        };
        req.context.people = 1;
        req.weights
            .entry("rail_home".to_owned())
            .or_default()
            .insert("idle".to_owned(), -1e9);
        let res = plan(&req);
        let planned = res.surfaces.get("rail_home").copied();
        assert_eq!(planned.map(|p| p.score), Some(20.0));
        assert_eq!(planned.map(|p| p.state), Some(State::Min));
    }

    #[test]
    fn other_modes_hide_ambient_surfaces() {
        let mut req = PlanRequest {
            now_ms: 1,
            surfaces: vec![
                surface("rail_home", 90.0, None),
                surface("chat", 60.0, None),
            ],
            ..PlanRequest::default()
        };
        req.context.mode = "brain".to_owned();
        let res = plan(&req);
        assert_eq!(res.context_key, "brain");
        assert_eq!(state_of(&res, "rail_home"), Some(State::Hidden));
        assert_eq!(state_of(&res, "chat"), Some(State::Shown));
    }
}
