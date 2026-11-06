use nuxiva_dialog_core::{AddresseeRules, Context, MAX_TEXT};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_ALIASES: usize = 32;
const MAX_NAME: usize = 128;
const MAX_NAMES: usize = 64;
const MAX_LAST: usize = 32_000;
const MAX_VOICES: u32 = 64;

fn bounded(value: f64, lo: f64, hi: f64, fallback: f64) -> f64 {
    if value.is_nan() {
        fallback
    } else {
        value.clamp(lo, hi)
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustAddressee {
    inner: AddresseeRules,
}

#[pymethods]
impl RustAddressee {
    #[new]
    #[allow(clippy::needless_pass_by_value)]
    #[pyo3(signature = (name, aliases=Vec::new()))]
    fn new(name: &str, aliases: Vec<String>) -> PyResult<Self> {
        if name.len() > MAX_NAME || aliases.len() > MAX_ALIASES {
            return Err(PyValueError::new_err("dialog.addressee.name_invalid"));
        }
        AddresseeRules::new(name, &aliases)
            .map(|inner| Self { inner })
            .map_err(|_| PyValueError::new_err("dialog.addressee.name_invalid"))
    }

    fn named(&self, text: &str) -> bool {
        text.len() <= MAX_TEXT && self.inner.named(text)
    }

    #[allow(clippy::too_many_arguments, clippy::fn_params_excessive_bools)]
    #[pyo3(signature = (text, *, alone, facing, asked_question, since_reply, last_turn=None, present_names=Vec::new(),
                        alone_score=0.35, threshold=0.5, same_speaker=None, voices_active=None, mixed_speakers=None))]
    fn judge(
        &self,
        py: Python<'_>,
        text: &str,
        alone: bool,
        facing: bool,
        asked_question: bool,
        since_reply: f64,
        last_turn: Option<String>,
        present_names: Vec<String>,
        alone_score: f64,
        threshold: f64,
        same_speaker: Option<bool>,
        voices_active: Option<u32>,
        mixed_speakers: Option<bool>,
    ) -> PyResult<(bool, f64, String)> {
        if last_turn.as_ref().is_some_and(|t| t.len() > MAX_LAST)
            || present_names.len() > MAX_NAMES
            || present_names.iter().any(|n| n.len() > MAX_NAME)
        {
            return Err(PyValueError::new_err("dialog.addressee.context_too_large"));
        }
        let ctx = Context {
            alone,
            facing,
            asked_question,
            since_reply: bounded(since_reply, 0.0, f64::INFINITY, f64::INFINITY),
            last_turn,
            present_names,
            alone_score: bounded(alone_score, 0.0, 1.0, 0.35),
            threshold: bounded(threshold, 0.2, 0.95, 0.5),
            same_speaker,
            voices_active: voices_active.map(|n| n.min(MAX_VOICES)),
            mixed_speakers,
        };
        let text = text.to_owned();
        let verdict = py.detach(|| self.inner.judge(&text, &ctx));
        Ok((verdict.directed, verdict.score, verdict.reason()))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustAddressee>()
}
