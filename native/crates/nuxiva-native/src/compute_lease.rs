use std::time::Instant;

use agency_scheduler::leases::{JobLease, LeaseError, Owner};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn lease_error(error: LeaseError) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustComputeLease {
    owner: Owner,
    job: JobLease,
    clock: Instant,
}

#[pymethods]
impl RustComputeLease {
    #[new]
    fn new(tenant: String, account: String) -> Self {
        let owner = Owner { tenant, account };
        let job = JobLease::new(owner.clone());
        Self {
            owner,
            job,
            clock: Instant::now(),
        }
    }

    fn assign(&mut self, worker: String, duration: u64) -> PyResult<u64> {
        self.job
            .assign(
                &self.owner,
                worker,
                self.clock.elapsed().as_secs(),
                duration,
            )
            .map(|lease| lease.generation)
            .map_err(lease_error)
    }

    fn validate(&self, worker: &str, generation: u64) -> PyResult<()> {
        self.job
            .validate(
                &self.owner,
                worker,
                generation,
                self.clock.elapsed().as_secs(),
            )
            .map_err(lease_error)
    }

    fn complete(&mut self, worker: &str, generation: u64) -> PyResult<()> {
        self.job
            .complete(
                &self.owner,
                worker,
                generation,
                self.clock.elapsed().as_secs(),
            )
            .map_err(lease_error)
    }
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<RustComputeLease>()
}
