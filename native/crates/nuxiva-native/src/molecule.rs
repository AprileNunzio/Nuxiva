use nuxiva_molecule_core::{Built, ColorScheme, Format, Limits, Lod, build, parse};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

fn options(format: &str, lod: &str, scheme: &str) -> PyResult<(Format, Lod, ColorScheme)> {
    let format = match format {
        "pdb" => Format::Pdb,
        "cif" => Format::Cif,
        "auto" => Format::Auto,
        _ => return Err(PyValueError::new_err("molecule_unknown_format")),
    };
    let lod = match lod {
        "atoms" => Lod::Atoms,
        "backbone" => Lod::Backbone,
        _ => return Err(PyValueError::new_err("molecule_unknown_lod")),
    };
    let scheme = match scheme {
        "element" => ColorScheme::Element,
        "chain" => ColorScheme::Chain,
        "secondary" => ColorScheme::Secondary,
        _ => return Err(PyValueError::new_err("molecule_unknown_scheme")),
    };
    Ok((format, lod, scheme))
}

fn pack(built: &Built) -> PyResult<Vec<u8>> {
    let atoms = u32::try_from(built.positions.len() / 4)
        .map_err(|_| PyValueError::new_err("molecule_too_many_atoms"))?;
    let bonds = u32::try_from(built.bonds.len() / 2)
        .map_err(|_| PyValueError::new_err("molecule_too_many_atoms"))?;
    let size = built
        .positions
        .len()
        .checked_mul(4)
        .and_then(|p| p.checked_add(built.colors.len()))
        .and_then(|p| p.checked_add(built.bonds.len().checked_mul(4)?))
        .and_then(|p| p.checked_add(8))
        .ok_or_else(|| PyValueError::new_err("molecule_too_large"))?;
    let mut out = Vec::with_capacity(size);
    out.extend_from_slice(&atoms.to_le_bytes());
    out.extend_from_slice(&bonds.to_le_bytes());
    built
        .positions
        .iter()
        .for_each(|v| out.extend_from_slice(&v.to_le_bytes()));
    out.extend_from_slice(&built.colors);
    built
        .bonds
        .iter()
        .for_each(|v| out.extend_from_slice(&v.to_le_bytes()));
    Ok(out)
}

#[pyfunction]
#[pyo3(signature = (data, format = "auto", lod = "atoms", scheme = "element"))]
pub fn molecule_build<'py>(
    py: Python<'py>,
    data: &[u8],
    format: &str,
    lod: &str,
    scheme: &str,
) -> PyResult<(String, Bound<'py, PyBytes>)> {
    let (format, lod, scheme) = options(format, lod, scheme)?;
    if data.len() > Limits::default().max_bytes {
        return Err(PyValueError::new_err("molecule_too_large"));
    }
    let owned = data.to_vec();
    let built = py
        .detach(move || parse(&owned, format, Limits::default()).map(|s| build(&s, lod, scheme)))
        .map_err(|e| PyValueError::new_err(e.code()))?;
    let summary = serde_json::to_string(&built.summary)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    let packed = pack(&built)?;
    Ok((summary, PyBytes::new(py, &packed)))
}
