use std::collections::BTreeMap;
use std::sync::RwLock;

use nuxiva_cortex_core::platform::crypto::{self, SecretKey, Signer};
use nuxiva_cortex_core::platform::sanitizer;
use nuxiva_cortex_core::slots::types::{SlotDefinition, SlotValue};
use nuxiva_cortex_core::slots::validator;
use nuxiva_cortex_core::{CortexError as CoreError, Decision, NeuronIndex, Thresholds};
use pyo3::create_exception;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::errors::poisoned;

create_exception!(nuxiva_native, CortexError, PyValueError);

fn failure(error: CoreError) -> PyErr {
    CortexError::new_err(error.code())
}

type DecisionRow = (
    &'static str,
    Option<&'static str>,
    Option<String>,
    f32,
    f32,
    f32,
);

fn decision_row(decision: Decision) -> DecisionRow {
    (
        decision.verdict.as_str(),
        decision.reason.map(nuxiva_cortex_core::SlowReason::as_str),
        decision.neuron_id,
        decision.positive_similarity,
        decision.negative_similarity,
        decision.synaptic_weight,
    )
}

fn thresholds_from(values: Option<(f32, f32, f32, f32, f32)>) -> Thresholds {
    values.map_or_else(
        Thresholds::default,
        |(fast_similarity, grey_similarity, inhibition_limit, fast_weight, grey_weight)| {
            Thresholds {
                fast_similarity,
                grey_similarity,
                inhibition_limit,
                fast_weight,
                grey_weight,
            }
        },
    )
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustNeuronIndex {
    inner: RwLock<NeuronIndex>,
}

impl RustNeuronIndex {
    fn read<T>(&self, action: impl FnOnce(&NeuronIndex) -> T) -> PyResult<T> {
        self.inner
            .read()
            .map(|guard| action(&guard))
            .map_err(|_| poisoned())
    }

    fn write<T>(&self, action: impl FnOnce(&mut NeuronIndex) -> T) -> PyResult<T> {
        self.inner
            .write()
            .map(|mut guard| action(&mut guard))
            .map_err(|_| poisoned())
    }
}

#[allow(clippy::needless_pass_by_value)]
#[pymethods]
impl RustNeuronIndex {
    #[new]
    fn new(dimension: usize) -> PyResult<Self> {
        Ok(Self {
            inner: RwLock::new(NeuronIndex::new(dimension).map_err(failure)?),
        })
    }

    #[staticmethod]
    fn from_snapshot_json(snapshot: &str) -> PyResult<Self> {
        Ok(Self {
            inner: RwLock::new(NeuronIndex::from_snapshot_json(snapshot).map_err(failure)?),
        })
    }

    fn dimension(&self) -> PyResult<usize> {
        self.read(NeuronIndex::dimension)
    }

    fn __len__(&self) -> PyResult<usize> {
        self.read(NeuronIndex::len)
    }

    fn neuron_ids(&self) -> PyResult<Vec<String>> {
        self.read(NeuronIndex::neuron_ids)
    }

    fn weight(&self, neuron_id: &str) -> PyResult<Option<f32>> {
        self.read(|index| index.weight(neuron_id))
    }

    fn upsert(&self, neuron_id: &str, weight: f32, dendrites: Vec<Vec<f32>>) -> PyResult<()> {
        self.write(|index| index.upsert(neuron_id, weight, &dendrites))?
            .map_err(failure)
    }

    fn remove(&self, neuron_id: &str) -> PyResult<bool> {
        self.write(|index| index.remove(neuron_id))
    }

    fn set_weight(&self, neuron_id: &str, weight: f32) -> PyResult<()> {
        self.write(|index| index.set_weight(neuron_id, weight))?
            .map_err(failure)
    }

    fn add_dendrite(&self, neuron_id: &str, vector: Vec<f32>) -> PyResult<()> {
        self.write(|index| index.add_dendrite(neuron_id, &vector))?
            .map_err(failure)
    }

    fn add_inhibition(&self, neuron_id: &str, vector: Vec<f32>) -> PyResult<()> {
        self.write(|index| index.add_inhibition(neuron_id, &vector))?
            .map_err(failure)
    }

    fn similarity_to(&self, neuron_id: &str, vector: Vec<f32>) -> PyResult<f32> {
        self.read(|index| index.similarity_to(neuron_id, &vector))?
            .map_err(failure)
    }

    #[pyo3(signature = (vector, thresholds = None))]
    fn route(
        &self,
        py: Python<'_>,
        vector: Vec<f32>,
        thresholds: Option<(f32, f32, f32, f32, f32)>,
    ) -> PyResult<DecisionRow> {
        let limits = thresholds_from(thresholds);
        let decision = py
            .detach(|| self.read(|index| index.route(&vector, &limits)))?
            .map_err(failure)?;
        Ok(decision_row(decision))
    }

    fn snapshot_json(&self) -> PyResult<String> {
        self.read(NeuronIndex::snapshot_json)?.map_err(failure)
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustSigner {
    inner: Signer,
}

#[pymethods]
impl RustSigner {
    #[new]
    #[pyo3(signature = (seed = None))]
    fn new(seed: Option<&[u8]>) -> PyResult<Self> {
        let inner = match seed {
            Some(bytes) => Signer::from_seed(bytes),
            None => Signer::generate(),
        };
        Ok(Self {
            inner: inner.map_err(failure)?,
        })
    }

    fn public_key<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.inner.public_key())
    }

    fn sign<'py>(&self, py: Python<'py>, message: &[u8]) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.inner.sign(message))
    }
}

#[pyfunction]
pub fn cortex_sanitize_utterance(text: &str, max_chars: usize) -> PyResult<String> {
    sanitizer::sanitize_utterance(text, max_chars).map_err(failure)
}

#[pyfunction]
pub fn cortex_sanitize_identifier(text: &str) -> PyResult<String> {
    sanitizer::sanitize_identifier(text).map_err(failure)
}

#[pyfunction]
pub fn cortex_generate_key(py: Python<'_>) -> PyResult<Bound<'_, PyBytes>> {
    let key = SecretKey::generate().map_err(failure)?;
    Ok(PyBytes::new(py, key.expose()))
}

#[pyfunction]
pub fn cortex_derive_key<'py>(
    py: Python<'py>,
    master: &[u8],
    context: &[u8],
) -> PyResult<Bound<'py, PyBytes>> {
    let key = SecretKey::derive(master, context).map_err(failure)?;
    Ok(PyBytes::new(py, key.expose()))
}

#[pyfunction]
pub fn cortex_seal<'py>(
    py: Python<'py>,
    key: &[u8],
    associated_data: &[u8],
    plaintext: &[u8],
) -> PyResult<Bound<'py, PyBytes>> {
    let secret = SecretKey::from_slice(key).map_err(failure)?;
    let sealed = crypto::seal(&secret, associated_data, plaintext).map_err(failure)?;
    Ok(PyBytes::new(py, &sealed))
}

#[pyfunction]
pub fn cortex_open<'py>(
    py: Python<'py>,
    key: &[u8],
    associated_data: &[u8],
    sealed: &[u8],
) -> PyResult<Bound<'py, PyBytes>> {
    let secret = SecretKey::from_slice(key).map_err(failure)?;
    let plaintext = crypto::open(&secret, associated_data, sealed).map_err(failure)?;
    Ok(PyBytes::new(py, &plaintext))
}

#[pyfunction]
pub fn cortex_verify(public_key: &[u8], message: &[u8], signature: &[u8]) -> PyResult<bool> {
    crypto::verify(public_key, message, signature).map_err(failure)
}

#[pyfunction]
pub fn cortex_validate_slots(schema_json: &str, extracted_json: &str) -> PyResult<String> {
    let definitions: Vec<SlotDefinition> =
        serde_json::from_str(schema_json).map_err(|_| failure(CoreError::SlotSchemaInvalid))?;
    let extracted: BTreeMap<String, String> =
        serde_json::from_str(extracted_json).map_err(|_| failure(CoreError::SlotTypeMismatch))?;
    let validated: BTreeMap<String, SlotValue> =
        validator::validate_slots(&definitions, &extracted).map_err(failure)?;
    serde_json::to_string(&validated).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
