use crate::cadence::Cadence;
use crate::lifecycle::Lifecycle;

#[derive(Debug, Clone)]
pub struct Entry {
    pub widget: String,
    pub screen: u16,
    pub state: Lifecycle,
    pub cadence: Cadence,
    pub cost_mb: f32,
    pub since_ms: u64,
    pub next_due_ms: Option<u64>,
}

impl Entry {
    #[must_use]
    pub fn schedule(&self, now_ms: u64) -> Option<u64> {
        if !self.state.refreshes() {
            return None;
        }
        self.cadence
            .period_ms(self.state == Lifecycle::Live)
            .map(|p| now_ms.saturating_add(p))
    }
}
