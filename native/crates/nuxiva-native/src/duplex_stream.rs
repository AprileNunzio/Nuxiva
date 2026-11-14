use std::sync::{Mutex, PoisonError};

use nuxiva_duplex_core::{
    AttributionChain, DuplexError, Pacer, PacerSettings, Verdict, WindowGate, WindowInput,
    parse_wav,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn fail(error: DuplexError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn verdict_code(verdict: Verdict) -> &'static str {
    match verdict {
        Verdict::Known => "known",
        Verdict::Guest => "guest",
        Verdict::Broadcast => "broadcast",
        Verdict::Uncertain => "uncertain",
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustGate {
    gate: Mutex<WindowGate>,
    chain: Mutex<AttributionChain>,
}

#[pymethods]
impl RustGate {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn push<'py>(
        &self,
        py: Python<'py>,
        frame: &[u8],
        voiced: bool,
    ) -> Option<(Bound<'py, pyo3::types::PyBytes>, bool)> {
        let samples: Vec<f32> = frame
            .chunks_exact(4)
            .filter_map(|b| Some(f32::from_le_bytes(b.try_into().ok()?)))
            .collect();
        let window = self
            .gate
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .push(&samples, voiced)?;
        let bytes: Vec<u8> = window
            .samples
            .iter()
            .flat_map(|s| s.to_le_bytes())
            .collect();
        Some((pyo3::types::PyBytes::new(py, &bytes), window.voiced))
    }

    fn release(&self) {
        self.gate
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .release();
    }

    fn busy(&self) -> bool {
        self.gate
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .busy()
    }

    fn reset(&self) {
        self.gate
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .reset();
        self.chain
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .reset();
    }

    fn quarantined(&self) -> bool {
        self.chain
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .quarantined()
    }

    #[pyo3(signature = (voiced, has_match, score, runner_up, limit, music, programme, echo_cancelled, slug=None))]
    #[allow(clippy::too_many_arguments, clippy::fn_params_excessive_bools)]
    fn judge(
        &self,
        voiced: bool,
        has_match: bool,
        score: f32,
        runner_up: f32,
        limit: f32,
        music: bool,
        programme: bool,
        echo_cancelled: bool,
        slug: Option<&str>,
    ) -> (String, u16) {
        let input = WindowInput {
            voiced,
            has_match,
            score,
            runner_up,
            limit,
            music,
            programme,
            echo_cancelled,
        };
        let ev = self
            .chain
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .judge(&input, slug);
        (verdict_code(ev.verdict).to_owned(), ev.margin_permille)
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustPacer {
    pacer: Mutex<Pacer>,
}

#[pymethods]
impl RustPacer {
    #[new]
    #[pyo3(signature = (frame_ms=40, lead_ms=240))]
    fn new(frame_ms: u32, lead_ms: u32) -> PyResult<Self> {
        Ok(Self {
            pacer: Mutex::new(Pacer::new(PacerSettings { frame_ms, lead_ms }).map_err(fail)?),
        })
    }

    fn push_wav(&self, epoch: u32, seq: u32, wav: &[u8]) -> PyResult<(u32, u32, u64)> {
        let pcm = parse_wav(wav).map_err(fail)?;
        let info = self
            .pacer
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .push(epoch, seq, &pcm)
            .map_err(fail)?;
        Ok((info.rate_hz, info.frames, info.duration_ms))
    }

    fn poll<'py>(
        &self,
        py: Python<'py>,
        now_ms: u64,
        live_epoch: u32,
    ) -> Vec<Bound<'py, pyo3::types::PyBytes>> {
        let frames = self
            .pacer
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .poll(now_ms, live_epoch);
        frames
            .iter()
            .map(|f| pyo3::types::PyBytes::new(py, &f.encode()))
            .collect()
    }

    fn cancel(&self) -> (u32, u64) {
        let dropped = self
            .pacer
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .cancel();
        (dropped.frames, dropped.duration_ms)
    }

    fn queued(&self) -> usize {
        self.pacer
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .queued_frames()
    }

    fn in_flight_ms(&self, now_ms: u64) -> u64 {
        self.pacer
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .in_flight_ms(now_ms)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustGate>()?;
    m.add_class::<RustPacer>()
}
