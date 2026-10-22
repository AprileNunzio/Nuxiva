use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (text, allowed = ""))]
pub(crate) fn detect_language(
    py: Python<'_>,
    text: &str,
    allowed: &str,
) -> Option<(String, f64, bool)> {
    py.detach(|| {
        let codes: Vec<&str> = allowed
            .split(',')
            .map(str::trim)
            .filter(|c| !c.is_empty())
            .collect();
        nuxiva_langid::detect(text, &codes).map(|g| (g.code.to_owned(), g.confidence, g.reliable))
    })
}

#[pyfunction]
pub(crate) fn supported_languages() -> Vec<&'static str> {
    nuxiva_langid::supported()
}
