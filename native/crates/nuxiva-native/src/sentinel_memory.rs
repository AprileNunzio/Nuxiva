use nuxiva_memory_core::ops::{Rewritten, compact, erase, pin, relink};
use nuxiva_memory_core::profile::build;
use nuxiva_memory_core::store::{genesis, open_all, scan, seal};
use nuxiva_memory_core::{IndexKey, Policy, Search, Sighting, Who};
use nuxiva_sentinel_core::Day;
use nuxiva_sentinel_core::journal::Head;
use nuxiva_sentinel_core::keys::{new_day_key, open_day_key};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::collections::BTreeMap;
use zeroize::Zeroizing;

const MAX_JSON: usize = 32 * 1024;
const MAX_DAYS: usize = 32;

type Output<'py> = Option<(Bound<'py, PyBytes>, String, usize, usize)>;

fn bad<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn parse<T: serde::de::DeserializeOwned>(raw: &str) -> PyResult<T> {
    if raw.len() > MAX_JSON {
        return Err(PyValueError::new_err("memory input too large"));
    }
    serde_json::from_str(raw).map_err(bad)
}

fn output(py: Python<'_>, done: Option<Rewritten>) -> Output<'_> {
    done.map(|r| (PyBytes::new(py, &r.data), r.head.hex(), r.count, r.changed))
}

#[pyclass(module = "nuxiva_native")]
pub struct RustMemory {
    master: Zeroizing<Vec<u8>>,
    index: IndexKey,
    policy: Policy,
}

impl std::fmt::Debug for RustMemory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("RustMemory(..)")
    }
}

impl RustMemory {
    fn key(&self, wrapped: &[u8], day: &str) -> PyResult<(Day, Zeroizing<Vec<u8>>)> {
        let day = Day::parse(day).map_err(bad)?;
        let key = open_day_key(&self.master, &day, wrapped).map_err(bad)?;
        Ok((day, key))
    }
}

#[pymethods]
impl RustMemory {
    #[new]
    #[pyo3(signature = (master, policy_json = None))]
    fn new(master: &[u8], policy_json: Option<&str>) -> PyResult<Self> {
        let index = IndexKey::derive(master).map_err(bad)?;
        let policy = match policy_json {
            Some(raw) => Policy::with(&parse::<BTreeMap<_, u16>>(raw)?).map_err(bad)?,
            None => Policy::default(),
        };
        Ok(Self {
            master: Zeroizing::new(master.to_vec()),
            index,
            policy,
        })
    }

    fn new_day_key<'py>(&self, py: Python<'py>, day: &str) -> PyResult<Bound<'py, PyBytes>> {
        let day = Day::parse(day).map_err(bad)?;
        Ok(PyBytes::new(
            py,
            &new_day_key(&self.master, &day).map_err(bad)?,
        ))
    }

    #[pyo3(signature = (wrapped, day, prev, sighting_json))]
    fn seal<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        prev: Option<&str>,
        sighting_json: &str,
    ) -> PyResult<(Bound<'py, PyBytes>, String)> {
        let (day, key) = self.key(wrapped, day)?;
        let head = match prev {
            Some(h) => Head::from_hex(h).map_err(bad)?,
            None => genesis(&day),
        };
        let sighting: Sighting = parse(sighting_json)?;
        let (frame, next) = seal(&key, &day, &head, &self.index, &sighting).map_err(bad)?;
        Ok((PyBytes::new(py, &frame), next.hex()))
    }

    #[staticmethod]
    fn verify(day: &str, data: &[u8]) -> PyResult<(String, usize, usize, bool)> {
        let day = Day::parse(day).map_err(bad)?;
        let s = scan(&day, data).map_err(bad)?;
        Ok((s.head.hex(), s.frames.len(), s.valid_len, s.truncated))
    }

    fn open(&self, wrapped: &[u8], day: &str, data: &[u8]) -> PyResult<String> {
        let (day, key) = self.key(wrapped, day)?;
        json(&open_all(&key, &day, data).map_err(bad)?)
    }

    fn search(&self, search_json: &str, days: Vec<(Vec<u8>, String, Vec<u8>)>) -> PyResult<String> {
        if days.len() > MAX_DAYS {
            return Err(PyValueError::new_err("too many days"));
        }
        let search: Search = parse(search_json)?;
        search.validate().map_err(bad)?;
        let (mut hits, mut scanned, mut opened) = (Vec::new(), 0_usize, 0_usize);
        for (wrapped, day, data) in days {
            let (day, key) = self.key(&wrapped, &day)?;
            let (h, s, o) = search.day(&key, &day, &self.index, &data).map_err(bad)?;
            hits.extend(h);
            scanned = scanned.saturating_add(s);
            opened = opened.saturating_add(o);
        }
        json(&search.page(hits, scanned, opened).map_err(bad)?)
    }

    fn profile(&self, who_json: &str, days: Vec<(Vec<u8>, String, Vec<u8>)>) -> PyResult<String> {
        if days.len() > MAX_DAYS.saturating_mul(12) {
            return Err(PyValueError::new_err("too many days"));
        }
        let who: Who = parse(who_json)?;
        let target = self.index.who(&who);
        let mut mine = Vec::new();
        for (wrapped, day, data) in days {
            let (day, key) = self.key(&wrapped, &day)?;
            let scanned = scan(&day, &data).map_err(bad)?;
            for frame in scanned
                .frames
                .iter()
                .filter(|f| f.header.tokens.contains(&target))
            {
                let s = nuxiva_memory_core::store::open(&key, &day, frame).map_err(bad)?;
                if s.who == who {
                    mine.push(s);
                }
            }
        }
        json(&build(&mine))
    }

    fn erase<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        data: &[u8],
        who_json: &str,
    ) -> PyResult<Output<'py>> {
        let (day, key) = self.key(wrapped, day)?;
        let who: Who = parse(who_json)?;
        Ok(output(
            py,
            erase(&key, &day, &self.index, data, &who).map_err(bad)?,
        ))
    }

    fn relink<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        data: &[u8],
        from_json: &str,
        to_json: &str,
    ) -> PyResult<Output<'py>> {
        let (day, key) = self.key(wrapped, day)?;
        let (from, to): (Who, Who) = (parse(from_json)?, parse(to_json)?);
        Ok(output(
            py,
            relink(&key, &day, &self.index, data, &from, &to).map_err(bad)?,
        ))
    }

    fn compact<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        data: &[u8],
        age_days: u16,
    ) -> PyResult<Output<'py>> {
        let (day, key) = self.key(wrapped, day)?;
        Ok(output(
            py,
            compact(&key, &day, &self.index, data, &self.policy, age_days).map_err(bad)?,
        ))
    }

    fn pin<'py>(
        &self,
        py: Python<'py>,
        wrapped: &[u8],
        day: &str,
        data: &[u8],
        id: &str,
        pinned: bool,
    ) -> PyResult<Output<'py>> {
        let (day, key) = self.key(wrapped, day)?;
        Ok(output(
            py,
            pin(&key, &day, &self.index, data, id, pinned).map_err(bad)?,
        ))
    }

    fn day_expired(&self, age_days: u16) -> bool {
        self.policy.day_expired(age_days)
    }

    fn policy(&self) -> PyResult<String> {
        json(&self.policy)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMemory>()
}
