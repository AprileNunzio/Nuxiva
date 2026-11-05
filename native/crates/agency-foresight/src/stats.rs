use serde::{Deserialize, Serialize};

use crate::agent::AgentState;
use crate::num::{count, mean, round3};

pub const LEAN: f64 = 0.2;
pub const STRONG: f64 = 0.5;

#[derive(Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RoundStats {
    pub round: u16,
    pub mean: f64,
    pub spread: f64,
    pub support: f64,
    pub oppose: f64,
    pub neutral: f64,
    pub polarization: f64,
    pub active: u32,
    pub posts: u32,
    pub replies: u32,
    pub reposts: u32,
    pub likes: u32,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct Activity {
    pub active: u32,
    pub posts: u32,
    pub replies: u32,
    pub reposts: u32,
    pub likes: u32,
}

#[must_use]
pub fn measure(round: u16, agents: &[AgentState], activity: Activity) -> RoundStats {
    let n = agents.len();
    let total: f64 = agents.iter().map(|a| a.stance).sum();
    let avg = mean(total, n);
    let variance = mean(agents.iter().map(|a| (a.stance - avg).powi(2)).sum(), n);
    let share =
        |f: &dyn Fn(f64) -> bool| mean(count(agents.iter().filter(|a| f(a.stance)).count()), n);
    let support = share(&|s| s > LEAN);
    let oppose = share(&|s| s < -LEAN);
    let strong_for = share(&|s| s > STRONG);
    let strong_against = share(&|s| s < -STRONG);
    RoundStats {
        round,
        mean: round3(avg),
        spread: round3(variance.sqrt()),
        support: round3(support),
        oppose: round3(oppose),
        neutral: round3((1.0 - support - oppose).max(0.0)),
        polarization: round3((4.0 * strong_for * strong_against).min(1.0)),
        active: activity.active,
        posts: activity.posts,
        replies: activity.replies,
        reposts: activity.reposts,
        likes: activity.likes,
    }
}

#[must_use]
pub fn histogram(agents: &[AgentState]) -> Vec<u32> {
    let mut bins = vec![0_u32; 10];
    for agent in agents {
        let scaled = ((agent.stance + 1.0) * 5.0).floor().clamp(0.0, 9.0);
        let slot = bins
            .iter_mut()
            .zip(0_u8..)
            .find(|(_, i)| f64::from(*i) >= scaled);
        if let Some((bin, _)) = slot {
            *bin = bin.saturating_add(1);
        }
    }
    bins
}
