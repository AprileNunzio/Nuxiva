use nuxiva_sentinel_core::journal::{Opened, append, open, verify};
use nuxiva_sentinel_core::keys::{new_day_key, open_day_key};
use nuxiva_sentinel_core::{Day, Event, Group, Head, Query, Retention, checkpoint};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::collections::BTreeMap;
use zeroize::Zeroizing;

const MAX_JSON: usize = 64 * 1024;
const MAX_DAYS: usize = 32;

fn bad<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn sized(raw: &str) -> PyResult<&str> {
    if raw.len() > MAX_JSON {
        Err(PyValueError::new_err("sentinel input too large"))
    } else {
        Ok(raw)
    }
}

#[pyclass(module = "nuxiva_native")]
pub struct RustSentinel {
    master: Zeroizing<Vec<u8>>,
    seed: Zeroizing<Vec<u8>>,
    retention: Retention,
}

impl std::fmt::Debug for RustSentinel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("RustSentinel(..)")
    }
}

impl RustSentinel {
    fn day_open(&self, wrapped: &[u8], day: &str, data: &[u8]) -> PyResult<(Day, Opened)> {
        let day = Day::parse(day).map_err(bad)?;
        let key = open_day_key(&self.master, &day, wrapped).map_err(bad)?;
        let opened = open(&key, &day, data).map_err(bad)?;
        Ok((day, opened))
    }
}

#[pymethods]
impl RustSentinel {
    #[new]
    #[pyo3(signature = (master, seed, retention_json = None))]
    fn new(master: &[u8], seed: &[u8], retention_json: Option<&str>) -> PyResult<Self> {
        if master.len() != 32 || seed.len() != 32 {
            return Err(PyValueError::new_err("sentinel keys must be 32 bytes"));
        }
        let retention = match retention_json {
            Some(raw) => {
                let overrides: BTreeMap<Group, u16> =
                    serde_json::from_str(sized(raw)?).map_err(bad)?;
                Retention::with(&overrides).map_err(bad)?
            }
            None => Retention::default(),
        };
        Ok(Self {
            master: Zeroizing::new(master.to_vec()),
            seed: Zeroizing::new(seed.to_vec()),
            retention,
        })
    }

    fn new_day_key<'py>(&self, py: Python<'py>, day: &str) -> PyResult<Bound<'py, PyBytes>> {
        let day = Day::parse(day).map_err(bad)?;
        Ok(PyBytes::new(
            py,
            &new_day_key(&self.master, &day).map_err(bad)?,
        ))
    }

    #[pyo3(signature = (wrapped, day, prev, event_json))]
    fn append<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        prev: Option<&str>,
        event_json: &str,
    ) -> PyResult<(Bound<'py, PyBytes>, String)> {
        let day = Day::parse(day).map_err(bad)?;
        let key = open_day_key(&self.master, &day, wrapped).map_err(bad)?;
        let head = match prev {
            Some(h) => Head::from_hex(h).map_err(bad)?,
            None => Head::genesis(&day),
        };
        let event: Event = serde_json::from_str(sized(event_json)?).map_err(bad)?;
        let (frame, next) = append(&key, &day, &head, &event).map_err(bad)?;
        Ok((PyBytes::new(py, &frame), next.hex()))
    }

    fn open(&self, wrapped: &[u8], day: &str, data: &[u8]) -> PyResult<String> {
        json(&self.day_open(wrapped, day, data)?.1)
    }

    #[staticmethod]
    fn verify(day: &str, data: &[u8]) -> PyResult<(String, usize, usize, bool)> {
        let day = Day::parse(day).map_err(bad)?;
        let (head, count, valid, truncated) = verify(&day, data).map_err(bad)?;
        Ok((head.hex(), count, valid, truncated))
    }

    fn query(&self, query_json: &str, days: Vec<(Vec<u8>, String, Vec<u8>)>) -> PyResult<String> {
        if days.len() > MAX_DAYS {
            return Err(PyValueError::new_err("too many days"));
        }
        let query: Query = serde_json::from_str(sized(query_json)?).map_err(bad)?;
        let mut events = Vec::new();
        for (wrapped, day, data) in days {
            events.extend(self.day_open(&wrapped, &day, &data)?.1.events);
        }
        json(&query.run(events).map_err(bad)?)
    }

    fn compact<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        data: &[u8],
        now_ms: u64,
    ) -> PyResult<(Bound<'py, PyBytes>, Option<String>, usize)> {
        let (day, opened) = self.day_open(wrapped, day, data)?;
        let key = open_day_key(&self.master, &day, wrapped).map_err(bad)?;
        let mut head = Head::genesis(&day);
        let mut out = Vec::new();
        let mut kept = 0_usize;
        for event in opened
            .events
            .iter()
            .filter(|e| self.retention.keeps(e, now_ms))
        {
            let (frame, next) = append(&key, &day, &head, event).map_err(bad)?;
            out.extend_from_slice(&frame);
            head = next;
            kept = kept.saturating_add(1);
        }
        let removed = opened.count.saturating_sub(kept);
        let head = (kept > 0).then(|| head.hex());
        Ok((PyBytes::new(py, &out), head, removed))
    }

    fn day_expired(&self, day_end_ms: u64, now_ms: u64) -> bool {
        self.retention.day_expired(day_end_ms, now_ms)
    }

    fn retention(&self) -> PyResult<String> {
        json(&self.retention)
    }

    fn checkpoint<'py>(
        &self,
        py: Python<'py>,
        day: &str,
        count: usize,
        head: &str,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let day = Day::parse(day).map_err(bad)?;
        let head = Head::from_hex(head).map_err(bad)?;
        Ok(PyBytes::new(
            py,
            &checkpoint::sign(&self.seed, &day, count, &head).map_err(bad)?,
        ))
    }

    fn verify_checkpoint(
        &self,
        day: &str,
        count: usize,
        head: &str,
        signature: &[u8],
    ) -> PyResult<bool> {
        let day = Day::parse(day).map_err(bad)?;
        let head = Head::from_hex(head).map_err(bad)?;
        let public = checkpoint::public_key(&self.seed).map_err(bad)?;
        Ok(checkpoint::verify(&public, &day, count, &head, signature).is_ok())
    }
}
