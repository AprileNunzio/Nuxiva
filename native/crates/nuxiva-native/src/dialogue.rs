use std::sync::Mutex;

use nuxiva_dialog_core::{DialogueBook, KEEP, Turn, Windows};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

type Row = (String, String, String, f64, String);

const MAX_TEXT: usize = 16_000;

fn row(t: &Turn) -> Row {
    (
        t.text.clone(),
        t.reply.clone(),
        t.intent.clone(),
        t.at,
        t.who.clone(),
    )
}

fn turn(r: &Row) -> Turn {
    Turn::new(&r.0, &r.1, &r.2, r.3, &r.4)
}

fn device(name: &str) -> PyResult<&str> {
    if DialogueBook::valid_device(name) {
        Ok(name)
    } else {
        Err(PyValueError::new_err("dialog.memory.device_invalid"))
    }
}

fn text(value: &str) -> PyResult<&str> {
    if value.len() <= MAX_TEXT {
        Ok(value)
    } else {
        Err(PyValueError::new_err("dialog.memory.text_too_long"))
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustDialogue {
    inner: Mutex<DialogueBook>,
}

impl RustDialogue {
    fn with<T>(&self, f: impl FnOnce(&mut DialogueBook) -> T) -> PyResult<T> {
        let mut guard = self
            .inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("dialog.memory.poisoned"))?;
        Ok(f(&mut guard))
    }
}

#[pymethods]
impl RustDialogue {
    #[new]
    #[pyo3(signature = (stale=15.0 * 60.0, resume=6.0 * 3600.0, recall=24.0 * 3600.0))]
    fn new(stale: f64, resume: f64, recall: f64) -> PyResult<Self> {
        DialogueBook::new(Windows {
            stale,
            resume,
            recall,
        })
        .map(|b| Self {
            inner: Mutex::new(b),
        })
        .map_err(|_| PyRuntimeError::new_err("dialog.memory.patterns"))
    }

    #[staticmethod]
    fn keep() -> usize {
        KEEP
    }

    fn windows(&self) -> PyResult<(f64, f64, f64)> {
        self.with(|b| {
            let w = b.windows();
            (w.stale, w.resume, w.recall)
        })
    }

    fn knows(&self, name: &str) -> PyResult<bool> {
        self.with(|b| b.knows(name))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn load(&self, name: &str, rows: Vec<Row>) -> PyResult<bool> {
        let name = device(name)?;
        if rows.len() > KEEP.saturating_mul(4) {
            return Err(PyValueError::new_err("dialog.memory.too_many_rows"));
        }
        let turns = rows.iter().map(turn).collect();
        self.with(|b| b.load(name, turns))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn remember(&self, name: &str, row: Row) -> PyResult<Row> {
        let name = device(name)?;
        let t = turn(&row);
        let out = self::row(&t);
        self.with(|b| b.remember(name, t))?;
        Ok(out)
    }

    #[pyo3(signature = (name=None))]
    fn forget(&self, name: Option<&str>) -> PyResult<usize> {
        self.with(|b| b.forget(name))
    }

    fn recent(&self, name: &str, now: f64) -> PyResult<Vec<Row>> {
        self.with(|b| b.recent(name, now).into_iter().map(row).collect())
    }

    fn last(&self, name: &str, now: f64) -> PyResult<Option<Row>> {
        self.with(|b| b.last(name, now).map(row))
    }

    fn asked_question(&self, name: &str, now: f64) -> PyResult<bool> {
        self.with(|b| b.asked_question(name, now))
    }

    fn since_reply(&self, name: &str, now: f64) -> PyResult<f64> {
        self.with(|b| b.since_reply(name, now))
    }

    fn wants_resume(&self, value: &str) -> PyResult<bool> {
        let value = text(value)?;
        self.with(|b| b.wants_resume(value))
    }

    #[pyo3(signature = (name, now, query=""))]
    fn context(&self, name: &str, now: f64, query: &str) -> PyResult<String> {
        let query = text(query)?;
        self.with(|b| b.context(name, now, query))
    }

    fn resolve(&self, name: &str, value: &str, now: f64) -> PyResult<String> {
        let value = text(value)?;
        self.with(|b| b.resolve(name, value, now))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDialogue>()
}
