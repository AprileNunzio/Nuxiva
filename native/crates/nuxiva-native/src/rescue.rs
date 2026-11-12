use std::sync::{Mutex, MutexGuard};

use nuxiva_rescue_core::{
    Body, Engine, Evidence, Kind, MAX_BODIES, MAX_EVIDENCE, Policy, Posture, PostureConfig, Step,
    assess,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_JSON: usize = 262_144;
const SPEECH_ALARM: f64 = 0.5;
const ALL_CLEAR: f64 = 0.95;

fn kind_of(raw: &str) -> PyResult<Kind> {
    serde_json::from_value(serde_json::Value::String(raw.to_owned()))
        .map_err(|_| PyValueError::new_err("rescue.evidence.kind"))
}

fn finite(now: f64) -> PyResult<f64> {
    if now.is_finite() && now >= 0.0 {
        Ok(now)
    } else {
        Err(PyValueError::new_err("rescue.evidence.time"))
    }
}

fn to_json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|_| PyRuntimeError::new_err("rescue.encode"))
}

fn policy_of(raw: &str) -> PyResult<Policy> {
    Policy::from_json(raw).map_err(|e| PyValueError::new_err(e.code()))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustRescue {
    inner: Mutex<Engine>,
}

impl RustRescue {
    fn engine(&self) -> PyResult<MutexGuard<'_, Engine>> {
        self.inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("rescue.poisoned"))
    }

    fn run(&self, f: impl FnOnce(&mut Engine) -> Step) -> PyResult<String> {
        let mut engine = self.engine()?;
        to_json(&f(&mut engine))
    }
}

#[pymethods]
impl RustRescue {
    #[new]
    #[pyo3(signature = (policy=""))]
    fn new(policy: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Mutex::new(Engine::new(policy_of(policy)?)),
        })
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (kind, probability, confidence, source, at, now, room=None))]
    fn observe(
        &self,
        kind: &str,
        probability: f64,
        confidence: f64,
        source: String,
        at: f64,
        now: f64,
        room: Option<String>,
    ) -> PyResult<()> {
        let evidence = Evidence {
            kind: kind_of(kind)?,
            probability,
            confidence,
            source,
            room,
            at,
        };
        self.engine()?
            .observe(evidence, finite(now)?)
            .map_err(|e| PyValueError::new_err(e.code()))
    }

    fn update(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.update(now))
    }

    fn person_ok(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.person_ok(now))
    }

    fn need_help(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.need_help(now))
    }

    fn acknowledge(&self, tier: u8, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.acknowledge(tier, now))
    }

    fn dismiss(&self, now: f64) -> PyResult<String> {
        let now = finite(now)?;
        self.run(|e| e.dismiss(now))
    }

    fn timeline(&self) -> PyResult<String> {
        to_json(&self.engine()?.timeline())
    }

    fn policy(&self) -> PyResult<String> {
        to_json(self.engine()?.policy())
    }
}

#[pyfunction]
fn rescue_assess(evidence: &str, now: f64, policy: &str) -> PyResult<String> {
    if evidence.len() > MAX_JSON {
        return Err(PyValueError::new_err("rescue.evidence.too_large"));
    }
    let now = finite(now)?;
    let policy = policy_of(policy)?;
    let list: Vec<Evidence> = serde_json::from_str(evidence)
        .map_err(|_| PyValueError::new_err("rescue.evidence.format"))?;
    if list.len() > MAX_EVIDENCE {
        return Err(PyValueError::new_err("rescue.evidence.too_many"));
    }
    for e in &list {
        e.validate(now)
            .map_err(|err| PyValueError::new_err(err.code()))?;
    }
    to_json(&assess(&list, &policy, now))
}

#[pyfunction]
fn rescue_policy(policy: &str) -> PyResult<String> {
    to_json(&policy_of(policy)?)
}

#[pyfunction]
fn rescue_detect_speech(text: &str) -> (Option<String>, f64) {
    let verdict = nuxiva_ear_core::distress::analyze(text, false, false, 1.0);
    let best = [
        ("help_words", verdict.help),
        ("fire", verdict.fire),
        ("violence", verdict.threat),
    ]
    .into_iter()
    .fold(
        ("", 0.0_f64),
        |acc, item| if item.1 > acc.1 { item } else { acc },
    );
    if best.1 >= SPEECH_ALARM {
        return (Some(best.0.to_owned()), best.1);
    }
    if verdict.answer == Some(nuxiva_ear_core::distress::Answer::Ok) {
        return (Some("all_clear".to_owned()), ALL_CLEAR);
    }
    (None, 0.0)
}

#[pyfunction]
fn rescue_detect_visual(
    class_name: &str,
    score: f64,
    width: f64,
    height: f64,
) -> (Option<String>, f64) {
    let (kind, conf) = nuxiva_rescue_core::detect_visual(class_name, score, width, height);
    let kind_str = kind.map(|k| {
        serde_json::to_string(&k)
            .unwrap_or_default()
            .trim_matches('"')
            .to_owned()
    });
    (kind_str, conf)
}

type BodyTuple = (f64, f64, f64, f64, f64, bool);
type PostureTuple = (String, u32, &'static str, f64, f64, f64);

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustPosture {
    inner: Mutex<Posture>,
}

#[pymethods]
impl RustPosture {
    #[new]
    #[pyo3(signature = (fall_window_s=2.5, confirm_s=4.0, immobile_s=60.0, still_frac=0.04, max_gap_s=6.0))]
    fn new(
        fall_window_s: f64,
        confirm_s: f64,
        immobile_s: f64,
        still_frac: f64,
        max_gap_s: f64,
    ) -> PyResult<Self> {
        let config = PostureConfig {
            fall_window_s,
            confirm_s,
            immobile_s,
            still_frac,
            max_gap_s,
        };
        Posture::new(config)
            .map(|p| Self {
                inner: Mutex::new(p),
            })
            .ok_or_else(|| PyValueError::new_err("rescue.posture.config"))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn observe(
        &self,
        camera: &str,
        t: f64,
        frame_w: f64,
        frame_h: f64,
        bodies: Vec<BodyTuple>,
    ) -> PyResult<Vec<PostureTuple>> {
        if bodies.len() > MAX_BODIES * 4 {
            return Err(PyValueError::new_err("rescue.posture.too_many"));
        }
        let list: Vec<Body> = bodies
            .iter()
            .map(|&(x, y, w, h, score, rest)| Body {
                x,
                y,
                w,
                h,
                score,
                rest,
            })
            .collect();
        let mut engine = self
            .inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("rescue.poisoned"))?;
        Ok(engine
            .observe(camera, t, frame_w, frame_h, &list)
            .into_iter()
            .map(|e| {
                (
                    e.camera,
                    e.track,
                    e.kind.code(),
                    e.probability,
                    e.confidence,
                    e.at,
                )
            })
            .collect())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustRescue>()?;
    m.add_class::<RustPosture>()?;
    m.add_function(wrap_pyfunction!(rescue_assess, m)?)?;
    m.add_function(wrap_pyfunction!(rescue_policy, m)?)?;
    m.add_function(wrap_pyfunction!(rescue_detect_speech, m)?)?;
    m.add_function(wrap_pyfunction!(rescue_detect_visual, m)?)
}
