use crate::candidate::{Candidate, Size};
use crate::category::Category;
use crate::context::{Context, Previous, Screen};
use crate::grid::{Grid, Slot, rows_for};
use crate::nucleus::{self, Form, Nucleus};
use crate::policy::PlannerPolicy;
use crate::score::Parts;
use crate::select::{Reason, Scored, Selection, select};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Input {
    pub screen: Screen,
    pub context: Context,
    pub candidates: Vec<Candidate>,
    #[serde(default)]
    pub previous: Previous,
    pub now_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Placed {
    pub key: String,
    pub slot: Option<Slot>,
    pub muted: bool,
    pub since_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Explain {
    pub key: String,
    pub shown: bool,
    pub reason: Reason,
    pub score: f32,
    pub parts: Parts,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenePlan {
    pub screen: i32,
    pub rows: u8,
    pub cap: u8,
    pub nucleus: Nucleus,
    pub shown: Vec<Placed>,
    pub explain: Vec<Explain>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlanError {
    Policy,
}

type Layout = (Nucleus, Vec<(usize, Option<Slot>)>, Vec<Scored>);

fn anchor(category: Category, grid: &Grid) -> (f32, f32) {
    let (w, h) = (f32::from(grid.cols), f32::from(grid.rows));
    match category {
        Category::Safety => (w / 2.0, 0.0),
        Category::Conversation => (w / 2.0, h * 0.8),
        Category::Media | Category::Ambient => (w / 2.0, h),
        Category::Personal => (w, 0.0),
        Category::Home => (0.0, 0.0),
        Category::Work => (w / 2.0, h / 2.0),
        Category::Info => (0.0, h / 2.0),
        Category::System => (w, h / 2.0),
    }
}

fn arrange(
    items: &[Scored],
    cands: &[Candidate],
    previous: &Previous,
    rows: u8,
    zone: Option<Slot>,
) -> (Grid, Vec<(usize, Slot)>, Vec<Scored>) {
    let mut grid = Grid::new(rows);
    if let Some(z) = zone {
        grid.take(z);
    }
    let (mut placed, mut left) = (Vec::new(), Vec::new());
    let mut ordered: Vec<&Scored> = items.iter().collect();
    ordered.sort_by_key(|s| cands.get(s.index).is_none_or(|c| c.pinned.is_none()));
    for item in ordered {
        let Some(c) = cands.get(item.index) else {
            continue;
        };
        let (w, h) = c.size.cells();
        let wanted = c
            .pinned
            .or_else(|| previous.shown.get(&c.key).map(|(s, _)| *s))
            .filter(|s| s.w == w && s.h == h);
        let slot = match wanted {
            Some(s) if grid.free(s) => Some(s),
            _ if c.pinned.is_some() => None,
            _ => grid.fit(w, h, anchor(c.category(), &grid)),
        };
        match slot {
            Some(s) if grid.take(s) => placed.push((item.index, s)),
            _ => left.push(*item),
        }
    }
    (grid, placed, left)
}

fn lay(
    sel: &Selection,
    cands: &[Candidate],
    previous: &Previous,
    rows: u8,
    policy: &PlannerPolicy,
) -> Layout {
    if let Some(full) = sel
        .chosen
        .iter()
        .find(|s| cands.get(s.index).is_some_and(|c| c.size == Size::Full))
    {
        let mut shown = vec![(
            full.index,
            Some(Slot {
                col: 0,
                row: 0,
                w: 12,
                h: rows,
            }),
        )];
        let mut left = Vec::new();
        for s in sel.chosen.iter().filter(|s| s.index != full.index) {
            if cands
                .get(s.index)
                .is_some_and(|c| c.category() == Category::Safety)
            {
                shown.push((s.index, None));
            } else {
                left.push(*s);
            }
        }
        return (
            Nucleus {
                form: Form::WhisperPill,
                slot: None,
            },
            shown,
            left,
        );
    }
    let base = Grid::new(rows);
    let hero = nucleus::hero(&base);
    let (grid, placed, left) = arrange(&sel.chosen, cands, previous, rows, Some(hero));
    let free = 1.0 - f32::from(grid.used()) / f32::from(grid.total().max(1));
    if left.is_empty() && free >= policy.stream_free {
        return (
            Nucleus {
                form: Form::CoreHero,
                slot: Some(hero),
            },
            wrap(placed),
            left,
        );
    }
    let (grid, placed, left) = arrange(&sel.chosen, cands, previous, rows, None);
    let orb = nucleus::orb(&grid);
    let free = 1.0 - f32::from(grid.used()) / f32::from(grid.total().max(1));
    if let (true, Some(spot)) = (left.is_empty() && free >= policy.stream_free, orb) {
        return (
            Nucleus {
                form: Form::FloatingOrb,
                slot: Some(spot),
            },
            wrap(placed),
            left,
        );
    }
    let edge = nucleus::stream(&base);
    let (_, placed, left) = arrange(&sel.chosen, cands, previous, rows, Some(edge));
    (
        Nucleus {
            form: Form::AmbientStream,
            slot: Some(edge),
        },
        wrap(placed),
        left,
    )
}

fn wrap(placed: Vec<(usize, Slot)>) -> Vec<(usize, Option<Slot>)> {
    placed.into_iter().map(|(i, s)| (i, Some(s))).collect()
}

pub fn plan(input: &Input, policy: &PlannerPolicy) -> Result<ScenePlan, PlanError> {
    if !policy.valid() {
        return Err(PlanError::Policy);
    }
    let cands = &input.candidates;
    let rows = rows_for(input.screen.aspect);
    let sel = select(
        cands,
        &input.screen,
        &input.context,
        &input.previous,
        input.now_ms,
        policy,
    );
    let (nucleus, shown, left) = lay(&sel, cands, &input.previous, rows, policy);
    let full = nucleus.form == Form::WhisperPill;
    let mut explain = Vec::new();
    let mut placed = Vec::new();
    for (index, slot) in &shown {
        let Some(c) = cands.get(*index) else { continue };
        let since = input
            .previous
            .shown
            .get(&c.key)
            .map_or(input.now_ms, |(_, t)| *t);
        placed.push(Placed {
            key: c.key.clone(),
            slot: *slot,
            muted: sel.muted.contains(index),
            since_ms: since,
        });
        if let Some(s) = sel.chosen.iter().find(|s| s.index == *index) {
            explain.push(Explain {
                key: c.key.clone(),
                shown: true,
                reason: Reason::Shown,
                score: s.total,
                parts: s.parts,
            });
        }
    }
    let lost = left.iter().map(|s| {
        (
            *s,
            if full {
                Reason::Takeover
            } else {
                Reason::Space
            },
        )
    });
    for (s, reason) in sel.hidden.iter().copied().chain(lost) {
        if let Some(c) = cands.get(s.index) {
            explain.push(Explain {
                key: c.key.clone(),
                shown: false,
                reason,
                score: s.total,
                parts: s.parts,
            });
        }
    }
    explain.sort_by(|a, b| {
        b.shown
            .cmp(&a.shown)
            .then(b.score.total_cmp(&a.score))
            .then_with(|| a.key.cmp(&b.key))
    });
    Ok(ScenePlan {
        screen: input.screen.id,
        rows,
        cap: sel.cap,
        nucleus,
        shown: placed,
        explain,
    })
}
