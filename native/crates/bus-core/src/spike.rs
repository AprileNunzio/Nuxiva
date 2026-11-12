use std::sync::atomic::{AtomicUsize, Ordering};

pub const DEFAULT_BUFFER_SIZE: usize = 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TransmitterType {
    GlutamateExcitatory = 0,
    GabaInhibitory = 1,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SynapticSpike {
    pub source_neuron: u32,
    pub target_cluster: u32,
    pub potential: f32,
    pub transmitter: TransmitterType,
    pub emotion_vector: [f32; 4],
    pub payload_id: u64,
}

impl SynapticSpike {
    #[must_use]
    pub fn new(
        source_neuron: u32,
        target_cluster: u32,
        potential: f32,
        transmitter: TransmitterType,
        emotion_vector: [f32; 4],
        payload_id: u64,
    ) -> Self {
        Self {
            source_neuron,
            target_cluster,
            potential,
            transmitter,
            emotion_vector,
            payload_id,
        }
    }

    #[must_use]
    pub fn is_inhibitory(&self) -> bool {
        self.transmitter == TransmitterType::GabaInhibitory
    }
}

#[derive(Debug)]
pub struct RingBufferLockFree<T, const N: usize = DEFAULT_BUFFER_SIZE> {
    buffer: [Option<T>; N],
    head: AtomicUsize,
    tail: AtomicUsize,
}

impl<T: Clone, const N: usize> Default for RingBufferLockFree<T, N> {
    fn default() -> Self {
        let buffer: [Option<T>; N] = std::array::from_fn(|_| None);
        Self {
            buffer,
            head: AtomicUsize::new(0),
            tail: AtomicUsize::new(0),
        }
    }
}

impl<T: Clone, const N: usize> RingBufferLockFree<T, N> {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(&mut self, item: T) -> bool {
        let head = self.head.load(Ordering::Relaxed);
        let tail = self.tail.load(Ordering::Acquire);
        if head.wrapping_sub(tail) >= N {
            return false;
        }
        let Some(idx) = head.checked_rem(N) else {
            return false;
        };
        let Some(slot) = self.buffer.get_mut(idx) else {
            return false;
        };
        *slot = Some(item);
        self.head.store(head.wrapping_add(1), Ordering::Release);
        true
    }

    pub fn pop(&mut self) -> Option<T> {
        let tail = self.tail.load(Ordering::Relaxed);
        let head = self.head.load(Ordering::Acquire);
        if tail == head {
            return None;
        }
        let idx = tail.checked_rem(N)?;
        let item = self.buffer.get_mut(idx)?.take();
        self.tail.store(tail.wrapping_add(1), Ordering::Release);
        item
    }

    pub fn len(&self) -> usize {
        let head = self.head.load(Ordering::Relaxed);
        let tail = self.tail.load(Ordering::Relaxed);
        head.wrapping_sub(tail)
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

#[derive(Debug, Clone)]
pub struct SynapticWeightMatrix {
    rows: usize,
    cols: usize,
    weights: Vec<f32>,
    a_plus: f32,
    a_minus: f32,
    tau_plus: f32,
    tau_minus: f32,
}

impl SynapticWeightMatrix {
    #[must_use]
    pub fn new(rows: usize, cols: usize, default_weight: f32) -> Self {
        let safe_rows = rows.max(1);
        let safe_cols = cols.max(1);
        let total = safe_rows.saturating_mul(safe_cols);
        Self {
            rows: safe_rows,
            cols: safe_cols,
            weights: vec![default_weight; total],
            a_plus: 0.015,
            a_minus: 0.012,
            tau_plus: 20.0,
            tau_minus: 20.0,
        }
    }

    fn index(&self, row: usize, col: usize) -> Option<usize> {
        if row < self.rows && col < self.cols {
            row.checked_mul(self.cols).and_then(|r| r.checked_add(col))
        } else {
            None
        }
    }

    #[must_use]
    pub fn get(&self, pre: usize, post: usize) -> f32 {
        self.index(pre, post)
            .and_then(|i| self.weights.get(i).copied())
            .unwrap_or(0.0)
    }

    pub fn set(&mut self, pre: usize, post: usize, weight: f32) {
        if let Some(i) = self.index(pre, post) {
            if let Some(slot) = self.weights.get_mut(i) {
                *slot = weight.clamp(0.0, 1.0);
            }
        }
    }

    pub fn apply_stdp(
        &mut self,
        pre: usize,
        post: usize,
        delta_t_ms: f32,
        dopamine: f32,
        is_reward: bool,
    ) -> f32 {
        let Some(idx) = self.index(pre, post) else {
            return 0.0;
        };
        let current = self.weights.get(idx).copied().unwrap_or(0.0);
        let delta_w = if delta_t_ms > 0.0 && is_reward {
            let exp_term = (-delta_t_ms / self.tau_plus.max(0.1)).exp();
            self.a_plus * exp_term * (1.0 + dopamine.clamp(0.0, 1.0))
        } else {
            let exp_term = (delta_t_ms / self.tau_minus.max(0.1)).exp();
            -self.a_minus * exp_term
        };
        let updated = (current + delta_w).clamp(0.0, 1.0);
        if let Some(slot) = self.weights.get_mut(idx) {
            *slot = updated;
        }
        updated
    }
}
