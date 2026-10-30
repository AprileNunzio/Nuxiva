use serde::Serialize;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize)]
pub struct Progress {
    pub total: usize,
    pub pending: usize,
    pub running: usize,
    pub review: usize,
    pub done: usize,
    pub failed: usize,
    pub cancelled: usize,
    pub blocked: usize,
    pub percent: u8,
}

impl Progress {
    pub(crate) fn finish(mut self) -> Self {
        let relevant = self.total.saturating_sub(self.cancelled);
        self.percent = if relevant == 0 {
            0
        } else {
            let scaled = self
                .done
                .saturating_mul(100)
                .checked_div(relevant)
                .unwrap_or(0);
            u8::try_from(scaled.min(100)).unwrap_or(100)
        };
        self
    }
}
