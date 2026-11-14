use std::collections::HashMap;

use serde::Serialize;

use crate::chunker::{Backlog, ChunkSettings, Chunker};
use crate::error::{DuplexError, DuplexResult};
use crate::session::Session;

pub trait Synth {
    fn speak(&mut self, epoch: u32, seq: u32, text: &str) -> DuplexResult<()>;
    fn cancel(&mut self, epoch: u32);
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct Metrics {
    pub ttfb_ms: Option<u64>,
    pub chunks: u32,
    pub max_gap_ms: u64,
    pub underruns: u32,
    pub dropped: u32,
}

#[derive(Debug)]
pub struct Pipeline<S: Synth> {
    epoch: u32,
    synth: S,
    chunker: Chunker,
    backlog: Backlog,
    sizes: HashMap<u32, usize>,
    texts: HashMap<u32, String>,
    first_token_ms: Option<u64>,
    last_chunk_ms: Option<u64>,
    metrics: Metrics,
}

impl<S: Synth> Pipeline<S> {
    pub fn new(epoch: u32, synth: S, settings: ChunkSettings) -> DuplexResult<Self> {
        Ok(Self {
            epoch,
            synth,
            chunker: Chunker::new(settings)?,
            backlog: Backlog::default(),
            sizes: HashMap::new(),
            texts: HashMap::new(),
            first_token_ms: None,
            last_chunk_ms: None,
            metrics: Metrics::default(),
        })
    }

    fn enqueue(
        &mut self,
        session: &mut Session,
        chunks: Vec<String>,
        now_ms: u64,
    ) -> DuplexResult<()> {
        for text in chunks {
            let seq = session.next_out_seq(self.epoch)?;
            self.backlog
                .push(seq, text.clone(), self.chunker.queue_cap())?;
            self.sizes.insert(seq, text.chars().count());
            self.texts.insert(seq, text);
            self.metrics.chunks = self.metrics.chunks.saturating_add(1);
            if let Some(prev) = self.last_chunk_ms {
                self.metrics.max_gap_ms = self.metrics.max_gap_ms.max(now_ms.saturating_sub(prev));
            }
            self.last_chunk_ms = Some(now_ms);
        }
        Ok(())
    }

    fn guard(&mut self, session: &Session) -> DuplexResult<()> {
        if session.is_live(self.epoch) {
            return Ok(());
        }
        self.abandon();
        Err(DuplexError::Stale)
    }

    fn abandon(&mut self) {
        let lost = self.backlog.clear();
        self.metrics.dropped = self
            .metrics
            .dropped
            .saturating_add(u32::try_from(lost).unwrap_or(u32::MAX));
        self.chunker.reset();
        self.sizes.clear();
        self.texts.clear();
        self.synth.cancel(self.epoch);
    }

    pub fn on_token(
        &mut self,
        session: &mut Session,
        token: &str,
        now_ms: u64,
    ) -> DuplexResult<()> {
        self.guard(session)?;
        if self.first_token_ms.is_none() {
            self.first_token_ms = Some(now_ms);
        }
        let mut chunks = self.chunker.push(token, now_ms);
        chunks.extend(self.chunker.poll(now_ms));
        self.enqueue(session, chunks, now_ms)?;
        self.pump(session)
    }

    pub fn on_tick(&mut self, session: &mut Session, now_ms: u64) -> DuplexResult<()> {
        self.guard(session)?;
        let chunks = self.chunker.poll(now_ms);
        self.enqueue(session, chunks, now_ms)?;
        self.pump(session)
    }

    pub fn finish(&mut self, session: &mut Session, now_ms: u64) -> DuplexResult<()> {
        self.guard(session)?;
        let chunks = self.chunker.flush(now_ms);
        self.enqueue(session, chunks, now_ms)?;
        self.pump(session)
    }

    fn pump(&mut self, session: &Session) -> DuplexResult<()> {
        while let Some((seq, text)) = self.backlog.pop() {
            if !session.is_live(self.epoch) {
                self.abandon();
                return Err(DuplexError::Stale);
            }
            self.synth.speak(self.epoch, seq, &text)?;
        }
        Ok(())
    }

    pub fn on_cut(&mut self) {
        self.abandon();
    }

    pub fn on_audio_started(&mut self, now_ms: u64) {
        if self.metrics.ttfb_ms.is_none()
            && let Some(first) = self.first_token_ms
        {
            self.metrics.ttfb_ms = Some(now_ms.saturating_sub(first));
        }
    }

    pub fn on_underrun(&mut self) {
        self.metrics.underruns = self.metrics.underruns.saturating_add(1);
    }

    pub fn on_chunk_played(&mut self, session: &mut Session, seq: u32) -> DuplexResult<()> {
        let chars = self.sizes.remove(&seq).ok_or(DuplexError::Invalid)?;
        self.texts.remove(&seq);
        session.mark_spoken(self.epoch, u32::try_from(chars).unwrap_or(u32::MAX))
    }

    #[must_use]
    pub fn unspoken(&self) -> Vec<&str> {
        let mut keys: Vec<_> = self.texts.keys().copied().collect();
        keys.sort_unstable();
        keys.iter()
            .filter_map(|k| self.texts.get(k).map(String::as_str))
            .collect()
    }

    #[must_use]
    pub const fn metrics(&self) -> &Metrics {
        &self.metrics
    }

    #[must_use]
    pub const fn synth(&self) -> &S {
        &self.synth
    }
}
