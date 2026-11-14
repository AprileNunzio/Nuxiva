use std::sync::{Mutex, PoisonError};

use nuxiva_duplex_core::{
    Audio, Backchannel, BargeDetector, BargeSettings, ChunkSettings, Chunker, Control, Decision,
    DuplexError, Evidence, IntentCatalog, InterruptedReply, PreRoll, Session, Settings, Trigger,
    Verdict, WindowInput, judge_window, windowed_settings,
};
use nuxiva_taskq_core::CancelToken;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::Value;

fn fail(error: DuplexError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn to_json<T: serde::Serialize>(value: &T) -> Result<String, DuplexError> {
    serde_json::to_string(value).map_err(|_| DuplexError::Serialize)
}

fn trigger(code: &str) -> Result<Trigger, DuplexError> {
    serde_json::from_value(Value::String(code.to_owned())).map_err(|_| DuplexError::Invalid)
}

#[pyclass(module = "nuxiva_native", frozen, skip_from_py_object)]
#[derive(Debug, Clone)]
pub struct RustCancelFlag {
    token: CancelToken,
}

#[pymethods]
impl RustCancelFlag {
    fn is_cancelled(&self) -> bool {
        self.token.is_cancelled()
    }

    fn cancel(&self) {
        self.token.cancel();
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustDuplex {
    session: Mutex<Session>,
    settings: Settings,
}

impl RustDuplex {
    fn with<T>(&self, f: impl FnOnce(&mut Session) -> Result<T, DuplexError>) -> PyResult<T> {
        let mut guard = self.session.lock().unwrap_or_else(PoisonError::into_inner);
        f(&mut guard).map_err(fail)
    }
}

#[pymethods]
impl RustDuplex {
    #[new]
    #[pyo3(signature = (settings_json, now_ms))]
    fn new(settings_json: &str, now_ms: u64) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let session = Session::new(settings.clone(), now_ms).map_err(fail)?;
        Ok(Self {
            session: Mutex::new(session),
            settings,
        })
    }

    fn trigger(&self, code: &str, now_ms: u64) -> PyResult<String> {
        let t = trigger(code).map_err(fail)?;
        self.with(|s| to_json(&s.trigger(t, now_ms)?))
    }

    fn begin_reply(&self, now_ms: u64) -> PyResult<u32> {
        self.with(|s| s.begin_reply(now_ms))
    }

    fn next_seq(&self, epoch: u32) -> PyResult<u32> {
        self.with(|s| s.next_out_seq(epoch))
    }

    fn bind(&self, epoch: u32) -> PyResult<RustCancelFlag> {
        let token = CancelToken::new();
        self.with(|s| s.bind(epoch, token.clone()))?;
        Ok(RustCancelFlag { token })
    }

    fn mark_spoken(&self, epoch: u32, chars: u32) -> PyResult<()> {
        self.with(|s| s.mark_spoken(epoch, chars))
    }

    fn admit(&self, epoch: u32, seq: u32, now_ms: u64) -> PyResult<()> {
        self.with(|s| s.admit(epoch, seq, now_ms))
    }

    fn cut(&self, epoch: u32, now_ms: u64) -> PyResult<String> {
        self.with(|s| to_json(&s.cut(epoch, now_ms)?))
    }

    fn finish(&self, epoch: u32, now_ms: u64) -> PyResult<String> {
        self.with(|s| to_json(&s.finish_reply(epoch, now_ms)?))
    }

    fn tick(&self, now_ms: u64) -> PyResult<Option<String>> {
        self.with(|s| s.tick(now_ms).map(|state| to_json(&state)).transpose())
    }

    fn is_live(&self, epoch: u32) -> bool {
        self.session
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .is_live(epoch)
    }

    fn snapshot(&self) -> PyResult<String> {
        self.with(|s| to_json(&s.snapshot()))
    }

    fn interruption(&self) -> PyResult<String> {
        self.with(|s| to_json(&s.interruption()))
    }

    fn events(&self) -> PyResult<String> {
        self.with(|s| to_json(&s.drain_events()))
    }

    fn parse_control(&self, text: &str) -> PyResult<String> {
        Control::parse(text, &self.settings)
            .and_then(|c| c.encode())
            .map_err(fail)
    }

    fn decode_audio(&self, data: &[u8]) -> PyResult<(u32, u32, usize)> {
        let frame = Audio::decode(data, &self.settings).map_err(fail)?;
        Ok((frame.epoch, frame.seq, frame.pcm.len()))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustChunker {
    chunker: Mutex<Chunker>,
}

impl RustChunker {
    fn with<T>(&self, f: impl FnOnce(&mut Chunker) -> T) -> T {
        f(&mut self.chunker.lock().unwrap_or_else(PoisonError::into_inner))
    }
}

#[pymethods]
impl RustChunker {
    #[new]
    #[pyo3(signature = (settings_json=""))]
    fn new(settings_json: &str) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            ChunkSettings::default()
        } else {
            ChunkSettings::from_json(settings_json).map_err(fail)?
        };
        Ok(Self {
            chunker: Mutex::new(Chunker::new(settings).map_err(fail)?),
        })
    }

    fn push(&self, token: &str, now_ms: u64) -> Vec<String> {
        self.with(|c| c.push(token, now_ms))
    }

    fn poll(&self, now_ms: u64) -> Vec<String> {
        self.with(|c| c.poll(now_ms))
    }

    fn flush(&self, now_ms: u64) -> Vec<String> {
        self.with(|c| c.flush(now_ms))
    }

    fn reset(&self) {
        self.with(Chunker::reset);
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustBarge {
    detector: Mutex<BargeDetector>,
    backchannel: Backchannel,
}

fn verdict(code: &str) -> Result<Verdict, DuplexError> {
    serde_json::from_value(Value::String(code.to_owned())).map_err(|_| DuplexError::Invalid)
}

fn decision_json(decision: &Decision) -> Result<String, DuplexError> {
    let value = match decision {
        Decision::Hold => serde_json::json!({"decision": "hold"}),
        Decision::Duck => serde_json::json!({"decision": "duck"}),
        Decision::Restore => serde_json::json!({"decision": "restore"}),
        Decision::Cut(report) => serde_json::json!({"decision": "cut", "report": report}),
    };
    to_json(&value)
}

#[pymethods]
impl RustBarge {
    #[new]
    #[pyo3(signature = (settings_json="", windowed=false))]
    fn new(settings_json: &str, windowed: bool) -> PyResult<Self> {
        let settings = if windowed {
            windowed_settings()
        } else if settings_json.is_empty() {
            BargeSettings::default()
        } else {
            BargeSettings::from_json(settings_json).map_err(fail)?
        };
        Ok(Self {
            detector: Mutex::new(BargeDetector::new(settings).map_err(fail)?),
            backchannel: Backchannel::builtin().map_err(fail)?,
        })
    }

    fn step(
        &self,
        duplex: &RustDuplex,
        verdict_code: &str,
        margin_permille: u16,
        voiced: bool,
        frame_ms: u32,
        now_ms: u64,
    ) -> PyResult<String> {
        let ev = Evidence {
            verdict: verdict(verdict_code).map_err(fail)?,
            margin_permille,
            voiced,
            frame_ms,
        };
        let mut session = duplex
            .session
            .lock()
            .unwrap_or_else(PoisonError::into_inner);
        let mut detector = self.detector.lock().unwrap_or_else(PoisonError::into_inner);
        decision_json(&detector.step(&mut session, &ev, now_ms)).map_err(fail)
    }

    fn tick(&self, now_ms: u64) -> PyResult<String> {
        let mut detector = self.detector.lock().unwrap_or_else(PoisonError::into_inner);
        decision_json(&detector.tick(now_ms)).map_err(fail)
    }

    #[staticmethod]
    #[allow(clippy::too_many_arguments, clippy::fn_params_excessive_bools)]
    fn judge_window(
        voiced: bool,
        has_match: bool,
        score: f32,
        runner_up: f32,
        limit: f32,
        music: bool,
        programme: bool,
        echo_cancelled: bool,
    ) -> (String, u16) {
        let ev = judge_window(&WindowInput {
            voiced,
            has_match,
            score,
            runner_up,
            limit,
            music,
            programme,
            echo_cancelled,
        });
        let code = match ev.verdict {
            Verdict::Known => "known",
            Verdict::Guest => "guest",
            Verdict::Broadcast => "broadcast",
            Verdict::Uncertain => "uncertain",
        };
        (code.to_owned(), ev.margin_permille)
    }

    fn is_backchannel(&self, text: &str) -> bool {
        self.backchannel.is_backchannel(text)
    }

    fn stats(&self) -> PyResult<String> {
        let detector = self.detector.lock().unwrap_or_else(PoisonError::into_inner);
        to_json(detector.stats()).map_err(fail)
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustPreRoll {
    ring: Mutex<PreRoll>,
}

#[pymethods]
impl RustPreRoll {
    #[new]
    fn new(rate_hz: u32, ms: u32, bytes_per_sample: u32) -> PyResult<Self> {
        Ok(Self {
            ring: Mutex::new(PreRoll::new(rate_hz, ms, bytes_per_sample).map_err(fail)?),
        })
    }

    fn push(&self, pcm: &[u8]) {
        self.ring
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .push(pcm);
    }

    fn snapshot<'py>(&self, py: Python<'py>) -> Bound<'py, pyo3::types::PyBytes> {
        let data = self
            .ring
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .snapshot();
        pyo3::types::PyBytes::new(py, &data)
    }

    fn clear(&self) {
        self.ring
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .clear();
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustMerge {
    catalog: IntentCatalog,
}

#[pymethods]
impl RustMerge {
    #[new]
    #[pyo3(signature = (catalog_json=""))]
    fn new(catalog_json: &str) -> PyResult<Self> {
        let catalog = if catalog_json.is_empty() {
            IntentCatalog::builtin()
        } else {
            IntentCatalog::from_json(catalog_json)
        };
        Ok(Self {
            catalog: catalog.map_err(fail)?,
        })
    }

    fn classify(&self, text: &str) -> PyResult<String> {
        to_json(&self.catalog.classify(text)).map_err(fail)
    }

    #[staticmethod]
    #[pyo3(signature = (duplex, spoken_text, unspoken_ref=None))]
    fn interrupted(
        duplex: &RustDuplex,
        spoken_text: &str,
        unspoken_ref: Option<String>,
    ) -> PyResult<String> {
        let session = duplex
            .session
            .lock()
            .unwrap_or_else(PoisonError::into_inner);
        let note = session
            .interruption()
            .ok_or_else(|| fail(DuplexError::Transition))?;
        let reply = InterruptedReply::new(note, spoken_text, unspoken_ref).map_err(fail)?;
        to_json(&reply).map_err(fail)
    }

    fn plan(&self, interrupted_json: &str, text: &str) -> PyResult<String> {
        if interrupted_json.len() > 16_384 {
            return Err(fail(DuplexError::TooLarge));
        }
        let reply: InterruptedReply =
            serde_json::from_str(interrupted_json).map_err(|_| fail(DuplexError::Parse))?;
        to_json(&self.catalog.plan(&reply, text)).map_err(fail)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDuplex>()?;
    m.add_class::<RustCancelFlag>()?;
    m.add_class::<RustChunker>()?;
    m.add_class::<RustBarge>()?;
    m.add_class::<RustPreRoll>()?;
    m.add_class::<RustMerge>()
}
