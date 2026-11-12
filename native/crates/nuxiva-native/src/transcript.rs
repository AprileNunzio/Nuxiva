use std::collections::HashSet;

use nuxiva_ear_core::words::{
    Lexicon, MAX_TERMS, MAX_TOKENS, Segment, Token, assess, fold, phonetic, similarity,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

type Fix = (String, String, f64);

const MAX_TEXT: usize = 16_000;
const MAX_SEGMENTS: usize = 256;
const MAX_CONTEXT: usize = 512;
const MAX_PHRASES: usize = 256;

fn check(text: &str) -> PyResult<&str> {
    if text.len() <= MAX_TEXT {
        Ok(text)
    } else {
        Err(PyValueError::new_err("ear.words.text_too_long"))
    }
}

fn folded_set(items: &[String], limit: usize) -> PyResult<HashSet<String>> {
    if items.len() > limit || items.iter().any(|s| s.len() > MAX_TEXT) {
        return Err(PyValueError::new_err("ear.words.too_many"));
    }
    Ok(items
        .iter()
        .map(|s| fold(s))
        .filter(|s| !s.is_empty())
        .collect())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustLexicon {
    inner: Lexicon,
}

#[pymethods]
impl RustLexicon {
    #[new]
    #[allow(clippy::needless_pass_by_value)]
    fn new(terms: Vec<String>) -> PyResult<Self> {
        if terms.len() > MAX_TERMS || terms.iter().any(|t| t.len() > MAX_TEXT) {
            return Err(PyValueError::new_err("ear.words.too_many"));
        }
        Ok(Self {
            inner: Lexicon::new(&terms),
        })
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    #[allow(clippy::needless_pass_by_value)]
    #[pyo3(signature = (words, context=Vec::new()))]
    fn correct(
        &self,
        py: Python<'_>,
        words: Vec<(String, f64)>,
        context: Vec<String>,
    ) -> PyResult<(String, Vec<Fix>)> {
        if words.len() > MAX_TOKENS || words.iter().any(|(w, _)| w.len() > MAX_TEXT) {
            return Err(PyValueError::new_err("ear.words.too_many"));
        }
        let context = folded_set(&context, MAX_CONTEXT)?;
        let tokens: Vec<Token> = words
            .into_iter()
            .map(|(text, prob)| Token {
                text,
                prob: if prob.is_finite() {
                    prob.clamp(0.0, 1.0)
                } else {
                    0.0
                },
            })
            .collect();
        let (text, fixes) = py.detach(|| self.inner.correct(&tokens, &context));
        Ok((
            text,
            fixes
                .into_iter()
                .map(|f| (f.heard, f.term, f.score))
                .collect(),
        ))
    }
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
#[pyo3(signature = (segments, prompt="", phrases=Vec::new()))]
fn ear_assess_segments(
    segments: Vec<(String, f64, f64, f64)>,
    prompt: &str,
    phrases: Vec<String>,
) -> PyResult<(Vec<bool>, Vec<String>, f64)> {
    if segments.len() > MAX_SEGMENTS || segments.iter().any(|s| s.0.len() > MAX_TEXT) {
        return Err(PyValueError::new_err("ear.words.too_many"));
    }
    let phrases = folded_set(&phrases, MAX_PHRASES)?;
    let list: Vec<Segment> = segments
        .into_iter()
        .map(
            |(text, avg_logprob, no_speech_prob, compression_ratio)| Segment {
                text,
                avg_logprob,
                no_speech_prob,
                compression_ratio,
            },
        )
        .collect();
    let out = assess(&list, check(prompt)?, &phrases);
    Ok((
        out.keep,
        out.reasons.into_iter().map(str::to_owned).collect(),
        out.confidence,
    ))
}

#[pyfunction]
fn ear_phonetic(text: &str) -> PyResult<String> {
    Ok(phonetic(check(text)?))
}

#[pyfunction]
fn ear_similarity(heard: &str, term: &str) -> PyResult<f64> {
    Ok(similarity(check(heard)?, check(term)?))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustLexicon>()?;
    m.add_function(wrap_pyfunction!(ear_assess_segments, m)?)?;
    m.add_function(wrap_pyfunction!(ear_phonetic, m)?)?;
    m.add_function(wrap_pyfunction!(ear_similarity, m)?)
}
