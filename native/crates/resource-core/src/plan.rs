use std::collections::BTreeSet;

use crate::level::{budget_share, capacity_scale, classify, idle_limit_ms, mem_percent, pressure};
use crate::model::{Action, ActionKind, Budget, Class, Component, Input, Kind, Level, Plan};

const fn class_share(class: Class) -> u64 {
    match class {
        Class::Protected => 30,
        Class::High => 20,
        Class::Normal => 10,
        Class::Low => 5,
    }
}

fn budget_of(component: &Component, total: u64, level: Level) -> u64 {
    if let Some(explicit) = component.budget {
        return if component.class == Class::Protected {
            explicit
        } else {
            explicit
                .saturating_mul(budget_share(level))
                .checked_div(100)
                .unwrap_or(0)
        };
    }
    let base = total.saturating_mul(class_share(component.class)) / 100;
    if component.class == Class::Protected {
        base
    } else {
        base.saturating_mul(budget_share(level)) / 100
    }
}

fn release_kind(kind: Kind) -> ActionKind {
    match kind {
        Kind::Model => ActionKind::Unload,
        Kind::Widget | Kind::Surface => ActionKind::Hibernate,
        Kind::Cache => ActionKind::Drop,
        Kind::Process => ActionKind::Trim,
    }
}

fn decide(
    component: &Component,
    level: Level,
    budget: u64,
    cpu_busy: bool,
    scale: (u64, u64),
) -> Option<(ActionKind, &'static str, u64)> {
    if component.class == Class::Protected {
        return None;
    }
    if component.kind == Kind::Surface && !component.visible {
        return Some((ActionKind::Suspend, "hidden_surface", component.rss));
    }
    if !component.reclaimable {
        return None;
    }
    if component.idle_ms >= idle_limit_ms(level, scale) && !component.visible {
        return Some((release_kind(component.kind), "idle", component.rss));
    }
    if level >= Level::Critical && component.class == Class::Low {
        return Some((
            release_kind(component.kind),
            "critical_pressure",
            component.rss,
        ));
    }
    if component.rss > budget && level >= Level::Elevated {
        let excess = component.rss.saturating_sub(budget);
        let kind = if component.kind == Kind::Cache {
            ActionKind::Drop
        } else {
            ActionKind::Trim
        };
        return Some((kind, "over_budget", excess));
    }
    if cpu_busy && level >= Level::High && component.cpu_percent >= 50.0 && !component.visible {
        return Some((ActionKind::Throttle, "cpu_hog", 0));
    }
    None
}

#[must_use]
pub fn plan(input: &Input) -> Plan {
    let score = pressure(&input.system);
    let level = classify(score, input.previous);
    let total = input.system.mem_total;
    let cpu_busy = input.system.cpu_percent >= 75.0;
    let scale = capacity_scale(&input.system);
    let mut actions = Vec::new();
    let mut budgets = Vec::new();
    let mut protected = BTreeSet::new();
    for component in &input.components {
        let budget = budget_of(component, total, level);
        budgets.push(Budget {
            id: component.id.clone(),
            budget,
            rss: component.rss,
            over: component.rss > budget,
        });
        if component.class == Class::Protected {
            protected.insert(component.id.clone());
            continue;
        }
        if let Some((action, reason, reclaim)) = decide(component, level, budget, cpu_busy, scale) {
            actions.push(Action {
                id: component.id.clone(),
                action,
                reason,
                reclaim,
            });
        }
    }
    actions.sort_by(|a, b| {
        let order = |x: &Action| u8::from(x.action != ActionKind::Suspend);
        order(a)
            .cmp(&order(b))
            .then(b.reclaim.cmp(&a.reclaim))
            .then(a.id.cmp(&b.id))
    });
    let reclaim_total = actions
        .iter()
        .fold(0u64, |sum, a| sum.saturating_add(a.reclaim));
    budgets.sort_by(|a, b| a.id.cmp(&b.id));
    Plan {
        level,
        pressure: score,
        mem_percent: mem_percent(&input.system),
        actions,
        budgets,
        reclaim_total,
        protected: protected.into_iter().collect(),
    }
}
