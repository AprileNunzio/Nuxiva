use nuxiva_node_core::hexutil;
use nuxiva_peer_core::{PeerKey, TrustBook};
use nuxiva_peer_ledger::store;
use nuxiva_peer_ledger::{Ledger, LedgerError, Wire};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::path::Path;

fn reject(error: LedgerError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn key_from(seed_hex: &str) -> PyResult<PeerKey> {
    let seed: [u8; 32] = hexutil::decode(seed_hex)
        .map_err(|_| PyValueError::new_err("ledger.error.field"))?
        .try_into()
        .map_err(|_| PyValueError::new_err("ledger.error.field"))?;
    PeerKey::from_seed(&seed).map_err(|_| PyValueError::new_err("ledger.error.field"))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct PeerLedger {
    ledger: Ledger,
    key: PeerKey,
}

#[pymethods]
impl PeerLedger {
    #[new]
    fn new(seed_hex: &str) -> PyResult<Self> {
        let key = key_from(seed_hex)?;
        let mut ledger = Ledger::new(TrustBook::new());
        ledger.enroll(key.id()).map_err(reject)?;
        Ok(Self { ledger, key })
    }

    fn id(&self) -> String {
        self.key.id().to_owned()
    }

    fn enroll(&mut self, id: &str) -> PyResult<()> {
        self.ledger.enroll(id).map_err(reject)
    }

    fn revoke(&mut self, id: &str) -> bool {
        self.ledger.revoke(id)
    }

    fn trusts(&self, id: &str) -> bool {
        self.ledger.trust().trusts(id)
    }

    fn announce(&mut self, addrs: Vec<String>, now_ms: i64) -> PyResult<bool> {
        Ok(self
            .ledger
            .announce(&self.key, addrs, now_ms)
            .map_err(reject)?
            .is_some())
    }

    fn candidates(&self, id: &str) -> Vec<String> {
        self.ledger.candidates(id)
    }

    fn report_failure(&mut self, id: &str, addr: &str) {
        self.ledger.report_failure(id, addr);
    }

    fn report_success(&mut self, id: &str, addr: &str) {
        self.ledger.report_success(id, addr);
    }

    fn digest_request(&self) -> PyResult<String> {
        let bytes = self.ledger.digest_request().encode().map_err(reject)?;
        String::from_utf8(bytes).map_err(|_| PyValueError::new_err("ledger.error.field"))
    }

    fn handle(&mut self, wire: &str, now_ms: i64) -> PyResult<Option<String>> {
        let request = Wire::decode(wire.as_bytes()).map_err(reject)?;
        if let Some(reply) = self.ledger.answer(&request) {
            let bytes = reply.encode().map_err(reject)?;
            return String::from_utf8(bytes)
                .map(Some)
                .map_err(|_| PyValueError::new_err("ledger.error.field"));
        }
        self.ledger.absorb(request, now_ms);
        Ok(None)
    }

    fn absorb(&mut self, wire: &str, now_ms: i64) -> PyResult<usize> {
        let reply = Wire::decode(wire.as_bytes()).map_err(reject)?;
        Ok(self.ledger.absorb(reply, now_ms).applied)
    }

    fn save(&self, path: &str) -> PyResult<()> {
        store::save(&self.ledger, Path::new(path)).map_err(reject)
    }

    fn load(&mut self, path: &str, now_ms: i64) -> PyResult<()> {
        let trust = self.ledger.trust().clone();
        self.ledger = store::load(trust, Path::new(path), now_ms).map_err(reject)?;
        Ok(())
    }

    fn __len__(&self) -> usize {
        self.ledger.len()
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PeerLedger>()?;
    Ok(())
}
