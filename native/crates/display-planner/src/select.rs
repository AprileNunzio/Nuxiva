use crate::candidate::Candidate;
use crate::category::Category;
use crate::context::{Context, Mode, Previous, Screen};
use crate::policy::PlannerPolicy;
use crate::score::{Parts, score};
use nuxiva_display_domain::{AudienceKind, Sensitivity};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Reason {
    Shown,
    Privacy,
    Quarantine,
    Capability,
    Threshold,
    Exclusive,
    Merged,
    Budget,
    Cognitive,
    Space,
    Takeover,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Scored {
    pub index: usize,
    pub parts: Parts,
    pub total: f32,
    pub must: bool,
}

#[derive(Debug, Clone, Default)]
pub struct Selection {
    pub chosen: Vec<Scored>,
    pub muted: BTreeSet<usize>,
    pub hidden: Vec<(Scored, Reason)>,
    pub cap: u8,
}

#[must_use]
pub fn visible(c: &Candidate, ctx: &Context) -> bool {
    let level = c.sensitivity;
    let public = level == Sensitivity::Public;
    let alert = c.category() == Category::Safety && public;
    let allowed = match ctx.audience {
        AudienceKind::GuestOnly => ctx.guest_public && c.guest_safe && public,
        kind => kind.may_see(level, ctx.trust_guests),
    };
    if !(alert || allowed) {
        return false;
    }
    let owned = c
        .owner
        .as_ref()
        .is_none_or(|o| ctx.present.iter().any(|p| p == o));
    match level {
        Sensitivity::Personal => owned,
        Sensitivity::Sensitive => owned && ctx.alone,
        Sensitivity::Public | Sensitivity::Household => true,
    }
}

#[must_use]
pub fn cap_for(screen: &Screen, ctx: &Context, policy: &PlannerPolicy) -> u8 {
    if let Some(cap) = ctx.cap {
        return cap.min(32);
    }
    if matches!(screen.role.as_deref(), Some("work" | "visual")) {
        return policy.cap_wide;
    }
    match ctx.mode {
        Mode::Conversation => policy.cap_conversation,
        Mode::Project => policy.cap_project,
        Mode::Ambient => policy.cap_ambient,
    }
}

fn order(a: &Scored, b: &Scored, cands: &[Candidate]) -> std::cmp::Ordering {
    b.must
        .cmp(&a.must)
        .then(b.total.total_cmp(&a.total))
        .then_with(|| {
            cands
                .get(a.index)
                .map(|c| &c.key)
                .cmp(&cands.get(b.index).map(|c| &c.key))
        })
}

#[must_use]
pub fn select(
    cands: &[Candidate],
    screen: &Screen,
    ctx: &Context,
    previous: &Previous,
    now_ms: u64,
    policy: &PlannerPolicy,
) -> Selection {
    let mut out = Selection {
        cap: cap_for(screen, ctx, policy),
        ..Selection::default()
    };
    let mut pool = Vec::new();
    for (index, c) in cands.iter().enumerate().take(policy.max_candidates) {
        let parts = score(c, screen.budget, policy);
        let scored = Scored {
            index,
            parts,
            total: parts.total(),
            must: c.must_show(),
        };
        let reason = if c.quarantined {
            Some(Reason::Quarantine)
        } else if c.needs_webgl2 && !screen.webgl2 {
            Some(Reason::Capability)
        } else if !visible(c, ctx) {
            Some(Reason::Privacy)
        } else {
            let held = previous.shown.get(&c.key);
            let dwell =
                held.is_some_and(|(_, since)| now_ms.saturating_sub(*since) < policy.dwell_ms);
            let bar = if held.is_some() {
                policy.exit
            } else {
                policy.enter
            };
            (!scored.must && !dwell && scored.total < bar).then_some(Reason::Threshold)
        };
        match reason {
            Some(r) => out.hidden.push((scored, r)),
            None => pool.push(scored),
        }
    }
    pool.sort_by(|a, b| order(a, b, cands));
    let (mut groups, mut sources, mut media) = (BTreeSet::new(), BTreeSet::new(), false);
    let (mut spent, mut count) = (0.0_f32, 0_u8);
    for item in pool {
        let Some(c) = cands.get(item.index) else {
            continue;
        };
        if let Some(group) = &c.exclusive
            && !groups.insert(group.clone())
        {
            out.hidden.push((item, Reason::Exclusive));
            continue;
        }
        if let Some(source) = &c.source
            && !sources.insert(source.clone())
        {
            out.hidden.push((item, Reason::Merged));
            continue;
        }
        if !item.must {
            let cost = if c.cost.is_finite() {
                c.cost.max(0.0)
            } else {
                f32::MAX
            };
            if count >= out.cap {
                out.hidden.push((item, Reason::Cognitive));
                continue;
            }
            if spent + cost > screen.budget {
                out.hidden.push((item, Reason::Budget));
                continue;
            }
            spent += cost;
            count = count.saturating_add(1);
        }
        if c.media.is_some() {
            if media {
                out.muted.insert(item.index);
            }
            media = true;
        }
        out.chosen.push(item);
    }
    out
}
