use nuxiva_expr_core::{Fault, Host, MAX_ITEMS, Value, evaluate};
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

create_exception!(nuxiva_native, ExprRejected, PyValueError);

const MAX_DEPTH: usize = 32;

struct PyHost<'py> {
    names: Bound<'py, PyDict>,
    failure: Option<PyErr>,
    budget: usize,
}

fn too_big() -> PyErr {
    ExprRejected::new_err("dati troppo grandi")
}

impl<'py> PyHost<'py> {
    fn convert(&mut self, obj: &Bound<'py, PyAny>, depth: usize) -> PyResult<Value> {
        self.budget = self.budget.checked_sub(1).ok_or_else(too_big)?;
        if depth > MAX_DEPTH {
            return Err(too_big());
        }
        if obj.is_none() {
            return Ok(Value::Null);
        }
        if let Ok(b) = obj.cast::<PyBool>() {
            return Ok(Value::Bool(b.is_true()));
        }
        if obj.is_instance_of::<PyInt>() {
            return Ok(obj.extract::<i128>().map_or_else(
                |_| Value::Float(obj.extract::<f64>().unwrap_or(f64::INFINITY)),
                Value::Int,
            ));
        }
        if let Ok(f) = obj.cast::<PyFloat>() {
            return Ok(Value::Float(f.value()));
        }
        if let Ok(s) = obj.cast::<PyString>() {
            return Ok(Value::Str(s.to_str()?.to_owned()));
        }
        if let Ok(d) = obj.cast::<PyDict>() {
            if d.len() > MAX_ITEMS {
                return Err(too_big());
            }
            let mut pairs = Vec::with_capacity(d.len());
            for (k, v) in d.iter() {
                pairs.push((
                    self.convert(&k, depth.saturating_add(1))?,
                    self.convert(&v, depth.saturating_add(1))?,
                ));
            }
            return Ok(Value::Map(pairs));
        }
        if obj.is_instance_of::<PyList>() || obj.is_instance_of::<PyTuple>() {
            let len = obj.len()?;
            if len > MAX_ITEMS {
                return Err(too_big());
            }
            let mut items = Vec::with_capacity(len);
            for item in obj.try_iter()? {
                items.push(self.convert(&item?, depth.saturating_add(1))?);
            }
            return Ok(Value::List(items));
        }
        if obj.is_callable() {
            return Ok(Value::Func(String::new()));
        }
        Ok(Value::Opaque(obj.str()?.to_str()?.to_owned()))
    }

    fn keep(&mut self, err: PyErr) -> Fault {
        self.failure = Some(err);
        Fault::Host
    }
}

fn to_py<'py>(py: Python<'py>, value: &Value) -> PyResult<Bound<'py, PyAny>> {
    Ok(match value {
        Value::Null => py.None().into_bound(py),
        Value::Bool(b) => PyBool::new(py, *b).to_owned().into_any(),
        Value::Int(i) => i.into_pyobject(py)?.into_any(),
        Value::Float(f) => PyFloat::new(py, *f).into_any(),
        Value::Str(s) | Value::Opaque(s) | Value::Func(s) => PyString::new(py, s).into_any(),
        Value::List(items) => {
            let list = PyList::empty(py);
            for item in items {
                list.append(to_py(py, item)?)?;
            }
            list.into_any()
        }
        Value::Map(pairs) => {
            let dict = PyDict::new(py);
            for (k, v) in pairs {
                dict.set_item(to_py(py, k)?, to_py(py, v)?)?;
            }
            dict.into_any()
        }
    })
}

impl Host for PyHost<'_> {
    fn name(&mut self, name: &str) -> Result<Option<Value>, Fault> {
        let found = match self.names.get_item(name) {
            Ok(found) => found,
            Err(e) => return Err(self.keep(e)),
        };
        let Some(obj) = found else {
            return Ok(None);
        };
        if obj.is_callable() && !obj.is_instance_of::<PyDict>() {
            return Ok(Some(Value::Func(name.to_owned())));
        }
        self.budget = MAX_ITEMS;
        match self.convert(&obj, 0) {
            Ok(v) => Ok(Some(v)),
            Err(e) => Err(self.keep(e)),
        }
    }

    fn call(&mut self, name: &str, args: Vec<Value>) -> Result<Value, Fault> {
        let py = self.names.py();
        let result = (|| -> PyResult<Value> {
            let func = self
                .names
                .get_item(name)?
                .ok_or_else(|| ExprRejected::new_err(format!("funzione sconosciuta: {name}")))?;
            let items = args
                .iter()
                .map(|a| to_py(py, a))
                .collect::<PyResult<Vec<_>>>()?;
            let out = func.call1(PyTuple::new(py, items)?)?;
            self.budget = MAX_ITEMS;
            self.convert(&out, 0)
        })();
        result.map_err(|e| self.keep(e))
    }
}

#[pyfunction]
fn expr_evaluate<'py>(
    py: Python<'py>,
    source: &str,
    names: Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyAny>> {
    let mut host = PyHost {
        names,
        failure: None,
        budget: MAX_ITEMS,
    };
    match evaluate(source, &mut host) {
        Ok(value) => to_py(py, &value),
        Err(Fault::Expr(msg)) => Err(ExprRejected::new_err(msg)),
        Err(Fault::Host) => Err(host
            .failure
            .take()
            .unwrap_or_else(|| ExprRejected::new_err("errore della funzione"))),
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("ExprRejected", m.py().get_type::<ExprRejected>())?;
    m.add_function(wrap_pyfunction!(expr_evaluate, m)?)
}
