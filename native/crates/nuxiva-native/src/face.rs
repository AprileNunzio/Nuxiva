use std::sync::RwLock;

use nuxiva_face_core::{
    Entry, FaceBook, RowsError, Settings, Verdict, decode_rows, encode_rows, merge,
    person_threshold,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};

fn rows_error(e: RowsError) -> PyErr {
    PyValueError::new_err(e.code())
}

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("face.state.poisoned")
}

fn vector(bytes: &[u8], dim: usize) -> PyResult<Vec<f32>> {
    let rows = decode_rows(bytes, dim).map_err(rows_error)?;
    match rows.as_slice() {
        [one] => Ok(one.clone()),
        _ => Err(PyValueError::new_err("face.vector.shape")),
    }
}

fn verdict_dict<'py>(py: Python<'py>, v: &Verdict) -> PyResult<Bound<'py, PyDict>> {
    let d = PyDict::new(py);
    d.set_item("slug", v.slug.as_deref())?;
    d.set_item("best", v.best.as_deref())?;
    d.set_item("score", v.score)?;
    d.set_item("second", v.second.as_deref())?;
    d.set_item("second_score", v.second_score)?;
    d.set_item("ambiguous", v.ambiguous)?;
    d.set_item("twin", v.twin)?;
    d.set_item("reason", v.reason)?;
    Ok(d)
}

type PersonRows = (String, Vec<u8>, Option<Vec<u8>>, bool);

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustFaceBook {
    inner: RwLock<FaceBook>,
}

impl RustFaceBook {
    fn read<T>(&self, f: impl FnOnce(&FaceBook) -> T) -> PyResult<T> {
        self.inner.read().map(|b| f(&b)).map_err(|_| lock_error())
    }

    fn dim(&self) -> PyResult<usize> {
        self.read(FaceBook::dim)
    }
}

#[pymethods]
impl RustFaceBook {
    #[new]
    #[pyo3(signature = (dim=128, base=0.40, margin=0.05, twin_margin=0.12, twin_sim=0.55, ir_weight=0.35, shadow_sim=0.62, learn_margin=0.08, adaptive=true))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        dim: usize,
        base: f32,
        margin: f32,
        twin_margin: f32,
        twin_sim: f32,
        ir_weight: f32,
        shadow_sim: f32,
        learn_margin: f32,
        adaptive: bool,
    ) -> PyResult<Self> {
        if !(nuxiva_face_core::MIN_DIM..=nuxiva_face_core::MAX_DIM).contains(&dim) {
            return Err(rows_error(RowsError::Dimension));
        }
        let settings = Settings {
            base,
            margin,
            twin_margin,
            twin_sim,
            ir_weight,
            shadow_sim,
            learn_margin,
            adaptive,
        };
        Ok(Self {
            inner: RwLock::new(FaceBook::new(dim, settings)),
        })
    }

    fn replace(&self, py: Python<'_>, people: Vec<PersonRows>) -> PyResult<usize> {
        let dim = self.dim()?;
        let mut entries = Vec::with_capacity(people.len());
        for (slug, rows, ir, auto) in people {
            let rows = decode_rows(&rows, dim).map_err(rows_error)?;
            let ir = ir
                .map(|b| decode_rows(&b, dim))
                .transpose()
                .map_err(rows_error)?;
            entries.push(Entry {
                slug,
                rows,
                ir,
                auto,
            });
        }
        let mut book = self.read(Clone::clone)?;
        py.detach(|| book.replace(entries));
        let count = book.len();
        *self.inner.write().map_err(|_| lock_error())? = book;
        Ok(count)
    }

    #[pyo3(signature = (feature, ir=None))]
    fn verdict<'py>(
        &self,
        py: Python<'py>,
        feature: &[u8],
        ir: Option<&[u8]>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let dim = self.dim()?;
        let probe = vector(feature, dim)?;
        let ir = ir.map(|b| vector(b, dim)).transpose()?;
        let v = self.read(|b| b.verdict(&probe, ir.as_deref()))?;
        verdict_dict(py, &v)
    }

    #[pyo3(signature = (feature, ir=None))]
    #[allow(clippy::type_complexity)]
    fn scores(
        &self,
        feature: &[u8],
        ir: Option<&[u8]>,
    ) -> PyResult<(Vec<(String, f32)>, Option<Vec<(String, f32)>>)> {
        let dim = self.dim()?;
        let probe = vector(feature, dim)?;
        let ir = ir.map(|b| vector(b, dim)).transpose()?;
        let (rgb, irs) = self.read(|b| b.scores(&probe, ir.as_deref()))?;
        Ok((
            rgb.into_iter().collect(),
            irs.map(|m| m.into_iter().collect()),
        ))
    }

    fn closest(&self, feature: &[u8]) -> PyResult<(Option<String>, f32)> {
        let probe = vector(feature, self.dim()?)?;
        self.read(|b| b.closest(&probe))
    }

    fn centroid_score(&self, slug: &str, feature: &[u8]) -> PyResult<Option<f32>> {
        let probe = vector(feature, self.dim()?)?;
        self.read(|b| b.centroid_score(slug, &probe))
    }

    #[pyo3(signature = (slug, feature, ir=None))]
    fn may_learn(&self, slug: &str, feature: &[u8], ir: Option<&[u8]>) -> PyResult<bool> {
        let dim = self.dim()?;
        let probe = vector(feature, dim)?;
        let ir = ir.map(|b| vector(b, dim)).transpose()?;
        self.read(|b| b.may_learn(slug, &probe, ir.as_deref()))
    }

    fn shadows(&self) -> PyResult<Vec<(String, String, f32)>> {
        self.read(FaceBook::shadows)
    }

    fn twins(&self) -> PyResult<Vec<(String, String, f32)>> {
        self.read(FaceBook::twins)
    }

    fn report<'py>(&self, py: Python<'py>) -> PyResult<Vec<Bound<'py, PyDict>>> {
        let rows = self.read(FaceBook::report)?;
        rows.iter()
            .map(|r| {
                let d = PyDict::new(py);
                d.set_item("slug", &r.slug)?;
                d.set_item("threshold", r.threshold)?;
                d.set_item("threshold_ir", r.threshold_ir)?;
                d.set_item("spread", r.spread)?;
                d.set_item("similar", r.similar.clone())?;
                d.set_item("shadow_of", r.shadow_of.as_deref())?;
                Ok(d)
            })
            .collect()
    }

    fn __len__(&self) -> PyResult<usize> {
        self.read(FaceBook::len)
    }
}

#[pyfunction]
#[pyo3(signature = (old, new, dim=128, limit=40))]
fn face_merge_rows<'py>(
    py: Python<'py>,
    old: Option<&[u8]>,
    new: &[u8],
    dim: usize,
    limit: usize,
) -> PyResult<Bound<'py, PyBytes>> {
    let old = old
        .map(|b| decode_rows(b, dim))
        .transpose()
        .map_err(rows_error)?
        .unwrap_or_default();
    let new = decode_rows(new, dim).map_err(rows_error)?;
    let merged = py.detach(|| merge(old, new, limit.clamp(1, nuxiva_face_core::MAX_ROWS)));
    Ok(PyBytes::new(py, &encode_rows(&merged)))
}

#[pyfunction]
#[pyo3(signature = (rows, dim=128, base=0.40))]
fn face_threshold(rows: &[u8], dim: usize, base: f32) -> PyResult<f32> {
    let rows = decode_rows(rows, dim).map_err(rows_error)?;
    Ok(person_threshold(&rows, dim, base))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustFaceBook>()?;
    m.add_function(wrap_pyfunction!(face_merge_rows, m)?)?;
    m.add_function(wrap_pyfunction!(face_threshold, m)?)?;
    Ok(())
}
