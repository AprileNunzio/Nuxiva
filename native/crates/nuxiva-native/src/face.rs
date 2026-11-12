use std::sync::RwLock;

use nuxiva_face_core::{
    Entry, FaceBook, Gray, ImageError, Landmarks, LivenessTracker, MARKS_DIM, Mark, RowsError,
    Settings, Verdict, assess, decode_raw, decode_rows, encode_rows, frame_issues, light, merge,
    person_threshold, signature,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use std::sync::Mutex;

fn rows_error(e: RowsError) -> PyErr {
    PyValueError::new_err(e.code())
}

fn image_error(e: ImageError) -> PyErr {
    PyValueError::new_err(e.code())
}

fn landmarks(values: &[f32]) -> PyResult<Landmarks> {
    Landmarks::from_slice(values).ok_or_else(|| PyValueError::new_err("face.landmarks.shape"))
}

fn marks_list<'py>(py: Python<'py>, marks: &[Mark]) -> PyResult<Vec<Bound<'py, PyDict>>> {
    marks
        .iter()
        .map(|m| {
            let d = PyDict::new(py);
            d.set_item("region", m.region)?;
            d.set_item("side", m.side)?;
            d.set_item("strength", m.strength)?;
            Ok(d)
        })
        .collect()
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

fn raw_marks(bytes: &[u8]) -> PyResult<Vec<f32>> {
    let rows = decode_raw(bytes, MARKS_DIM).map_err(rows_error)?;
    match rows.as_slice() {
        [one] => Ok(one.clone()),
        _ => Err(PyValueError::new_err("face.marks.shape")),
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

type PersonRows = (String, Vec<u8>, Option<Vec<u8>>, bool, Option<Vec<u8>>);

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
    #[pyo3(signature = (dim=128, base=0.40, margin=0.05, twin_margin=0.12, twin_sim=0.55, ir_weight=0.35, shadow_sim=0.62, learn_margin=0.08, adaptive=true, marks_margin=0.015))]
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
        marks_margin: f32,
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
            marks_margin,
            adaptive,
        };
        Ok(Self {
            inner: RwLock::new(FaceBook::new(dim, settings)),
        })
    }

    fn replace(&self, py: Python<'_>, people: Vec<PersonRows>) -> PyResult<usize> {
        let dim = self.dim()?;
        let mut entries = Vec::with_capacity(people.len());
        for (slug, rows, ir, auto, marks) in people {
            let rows = decode_rows(&rows, dim).map_err(rows_error)?;
            let ir = ir
                .map(|b| decode_rows(&b, dim))
                .transpose()
                .map_err(rows_error)?;
            let marks = marks
                .map(|b| decode_raw(&b, MARKS_DIM))
                .transpose()
                .map_err(rows_error)?
                .filter(|m| !m.is_empty());
            entries.push(Entry {
                slug,
                rows,
                ir,
                marks,
                auto,
            });
        }
        let mut book = self.read(Clone::clone)?;
        py.detach(|| book.replace(entries));
        let count = book.len();
        *self.inner.write().map_err(|_| lock_error())? = book;
        Ok(count)
    }

    #[pyo3(signature = (feature, ir=None, marks=None))]
    fn verdict<'py>(
        &self,
        py: Python<'py>,
        feature: &[u8],
        ir: Option<&[u8]>,
        marks: Option<&[u8]>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let dim = self.dim()?;
        let probe = vector(feature, dim)?;
        let ir = ir.map(|b| vector(b, dim)).transpose()?;
        let marks = marks.map(raw_marks).transpose()?;
        let v = self.read(|b| b.verdict_with_marks(&probe, ir.as_deref(), marks.as_deref()))?;
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
                d.set_item("marks", marks_list(py, &r.marks)?)?;
                d.set_item("marks_samples", r.marks_samples)?;
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

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustFaceLiveness {
    inner: Mutex<LivenessTracker>,
}

#[pymethods]
impl RustFaceLiveness {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    #[pyo3(signature = (points, now, minimum=0.55))]
    #[allow(clippy::needless_pass_by_value)]
    fn update<'py>(
        &self,
        py: Python<'py>,
        points: Vec<f32>,
        now: f64,
        minimum: f32,
    ) -> PyResult<Bound<'py, PyDict>> {
        let marks = landmarks(&points)?;
        let r = self.inner.lock().map_err(|_| lock_error())?.update(
            marks,
            now,
            minimum.clamp(0.1, 0.95),
        );
        let d = PyDict::new(py);
        d.set_item("state", r.state)?;
        d.set_item("score", r.score)?;
        d.set_item("depth", r.depth)?;
        d.set_item("turn", r.turn)?;
        d.set_item("flat_pairs", r.pairs)?;
        Ok(d)
    }
}

#[pyfunction]
fn face_marks<'py>(
    py: Python<'py>,
    gray: &[u8],
    width: usize,
    height: usize,
) -> PyResult<Bound<'py, PyBytes>> {
    let image = Gray::new(gray, width, height).map_err(image_error)?;
    let sig = py.detach(|| signature(&image));
    Ok(PyBytes::new(py, &encode_rows(&[sig])))
}

#[pyfunction]
fn face_light<'py>(
    py: Python<'py>,
    gray: &[u8],
    width: usize,
    height: usize,
) -> PyResult<Bound<'py, PyDict>> {
    let image = Gray::new(gray, width, height).map_err(image_error)?;
    let l = light(&image);
    let d = PyDict::new(py);
    d.set_item("mean", l.mean)?;
    d.set_item("std", l.std)?;
    d.set_item("dark_pct", l.dark_pct)?;
    d.set_item("bright_pct", l.bright_pct)?;
    d.set_item("issues", frame_issues(&l))?;
    Ok(d)
}

#[pyfunction]
#[pyo3(signature = (gray, width, height, points, face_w, frame_w))]
#[allow(clippy::needless_pass_by_value)]
fn face_quality<'py>(
    py: Python<'py>,
    gray: &[u8],
    width: usize,
    height: usize,
    points: Vec<f32>,
    face_w: f32,
    frame_w: f32,
) -> PyResult<Bound<'py, PyDict>> {
    let image = Gray::new(gray, width, height).map_err(image_error)?;
    let marks = landmarks(&points)?;
    let q = py.detach(|| assess(&image, &marks, face_w, frame_w));
    let d = PyDict::new(py);
    d.set_item("score", q.score)?;
    d.set_item("sharpness", q.sharpness)?;
    d.set_item("brightness", q.brightness)?;
    d.set_item("contrast", q.contrast)?;
    d.set_item("face_px", q.face_px)?;
    d.set_item("face_ratio", q.face_ratio)?;
    d.set_item("eye_px", q.eye_px)?;
    d.set_item("yaw", q.pose.yaw_deg)?;
    d.set_item("pitch", q.pose.pitch_deg)?;
    d.set_item("roll", q.pose.roll_deg)?;
    d.set_item("yaw_ratio", q.pose.yaw_ratio)?;
    d.set_item("pitch_ratio", q.pose.pitch_ratio)?;
    d.set_item("kind", q.kind)?;
    d.set_item("issues", q.issues)?;
    Ok(d)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("FACE_MARKS_DIM", MARKS_DIM)?;
    m.add_class::<RustFaceBook>()?;
    m.add_class::<RustFaceLiveness>()?;
    m.add_function(wrap_pyfunction!(face_marks, m)?)?;
    m.add_function(wrap_pyfunction!(face_light, m)?)?;
    m.add_function(wrap_pyfunction!(face_quality, m)?)?;
    m.add_function(wrap_pyfunction!(face_merge_rows, m)?)?;
    m.add_function(wrap_pyfunction!(face_threshold, m)?)?;
    Ok(())
}
