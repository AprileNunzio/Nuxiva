use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;

use ed25519_dalek::SigningKey;
use nuxiva_mcp_core::{
    AuditSink, CallRequest, Catalog, FileSink, Hub, McpError, PolicyConfig, Scope, Settings,
    SharedSecrets, SignedCatalog, ToolError, Within, generate_signing_key, resume_from_file,
    sign_catalog, verify_catalog,
};
use nuxiva_mcp_servers::{ServerDefinition, register_all};
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use tokio::runtime::{Builder, Runtime};

create_exception!(nuxiva_native, McpRejected, PyValueError);

fn rejected(error: McpError) -> PyErr {
    McpRejected::new_err(error.code())
}

fn json_of<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|_| rejected(McpError::Serialize))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustMcpEngine {
    runtime: Runtime,
    hub: Arc<Hub>,
    secrets: Arc<SharedSecrets>,
    max_message: usize,
    max_in_flight: usize,
}

#[pymethods]
impl RustMcpEngine {
    #[new]
    fn new(settings_json: &str, policy_json: &str, audit_path: &str) -> PyResult<Self> {
        let settings = Settings::from_json(settings_json).map_err(rejected)?;
        let (max_message, max_in_flight) = (settings.max_message_bytes, settings.max_in_flight);
        let policy = PolicyConfig::from_json(policy_json).map_err(rejected)?;
        let path = Path::new(audit_path);
        let resume = resume_from_file(path).map_err(rejected)?;
        let sink: Box<dyn AuditSink> = Box::new(FileSink::open(path).map_err(rejected)?);
        let secrets = Arc::new(SharedSecrets::default());
        let hub = Hub::new(settings, policy, Arc::clone(&secrets) as _, sink, resume)
            .map_err(rejected)?;
        let runtime = Builder::new_multi_thread()
            .worker_threads(2)
            .enable_all()
            .build()
            .map_err(|_| rejected(McpError::Io))?;
        Ok(Self {
            runtime,
            hub: Arc::new(hub),
            secrets,
            max_message,
            max_in_flight,
        })
    }

    fn apply_catalog(
        &self,
        signed_json: &str,
        public_key: &[u8],
        now: u64,
        last_serial: u64,
    ) -> PyResult<u64> {
        let key: [u8; 32] = public_key
            .try_into()
            .map_err(|_| rejected(McpError::SignatureInvalid))?;
        let signed: SignedCatalog =
            serde_json::from_str(signed_json).map_err(|_| rejected(McpError::InvalidSettings))?;
        let catalog = verify_catalog(&signed, &key, now, last_serial).map_err(rejected)?;
        let hub = Arc::clone(&self.hub);
        self.runtime
            .block_on(async move { hub.apply_catalog(&catalog).map(|()| catalog.serial) })
            .map_err(rejected)
    }

    #[staticmethod]
    fn generate_key(py: Python<'_>) -> PyResult<(Bound<'_, PyBytes>, Bound<'_, PyBytes>)> {
        let key = generate_signing_key().map_err(rejected)?;
        Ok((
            PyBytes::new(py, &key.to_bytes()),
            PyBytes::new(py, &key.verifying_key().to_bytes()),
        ))
    }

    #[staticmethod]
    fn sign_catalog(catalog_json: &str, secret_key: &[u8]) -> PyResult<String> {
        let seed: [u8; 32] = secret_key
            .try_into()
            .map_err(|_| rejected(McpError::SignatureInvalid))?;
        let catalog: Catalog =
            serde_json::from_str(catalog_json).map_err(|_| rejected(McpError::InvalidSettings))?;
        let signed = sign_catalog(&catalog, &SigningKey::from_bytes(&seed)).map_err(rejected)?;
        json_of(&signed)
    }

    fn set_internal(&self, definitions_json: &str) -> PyResult<()> {
        let definitions: Vec<ServerDefinition> = serde_json::from_str(definitions_json)
            .map_err(|_| rejected(McpError::InvalidSettings))?;
        register_all(
            self.hub.internal(),
            &definitions,
            self.runtime.handle(),
            self.max_message,
            self.max_in_flight,
        )
        .map_err(rejected)
    }

    fn needs_consent(&self, tool_id: &str, operation: &str) -> bool {
        self.hub.needs_consent(tool_id, operation)
    }

    fn set_secret(&self, id: &str, value: &str) {
        self.secrets.set(id, value);
    }

    fn remove_secret(&self, id: &str) {
        self.secrets.remove(id);
    }

    fn set_scopes(&self, scopes_json: &str) -> PyResult<()> {
        let scopes: HashMap<String, Scope> =
            serde_json::from_str(scopes_json).map_err(|_| rejected(McpError::InvalidSettings))?;
        self.hub.set_scopes(scopes);
        Ok(())
    }

    fn tools_json(&self) -> PyResult<String> {
        json_of(&self.hub.tools())
    }

    fn statuses_json(&self) -> PyResult<String> {
        json_of(&self.hub.statuses())
    }

    fn tools_version(&self) -> u64 {
        self.hub.tools_version()
    }

    fn approve(&self, tool_id: &str) -> PyResult<()> {
        self.hub.approve(tool_id).map_err(rejected)
    }

    fn request_consent(&self, request_json: &str) -> PyResult<String> {
        let request: CallRequest =
            serde_json::from_str(request_json).map_err(|_| rejected(McpError::InvalidArguments))?;
        self.hub.request_consent(&request).map_err(rejected)
    }

    fn call(&self, py: Python<'_>, request_json: &str) -> PyResult<String> {
        let request: CallRequest =
            serde_json::from_str(request_json).map_err(|_| rejected(McpError::InvalidArguments))?;
        let hub = Arc::clone(&self.hub);
        let output = py
            .detach(|| {
                self.runtime
                    .block_on(async move { hub.call(request).await })
            })
            .map_err(rejected)?;
        json_of(&output)
    }

    fn call_budgeted(&self, py: Python<'_>, request_json: &str) -> PyResult<String> {
        let request: CallRequest =
            serde_json::from_str(request_json).map_err(|_| rejected(McpError::InvalidArguments))?;
        let hub = Arc::clone(&self.hub);
        let within = py
            .detach(|| {
                self.runtime
                    .block_on(async move { hub.call_within(request).await })
            })
            .map_err(rejected)?;
        match within {
            Within::Done(output) => {
                json_of(&serde_json::json!({"state": "done", "output": output}))
            }
            Within::Pending(id) => json_of(&serde_json::json!({"state": "pending", "job": id})),
        }
    }

    fn job_status(&self, id: &str, agent: &str) -> PyResult<String> {
        let view = self.hub.poll(id, agent).map_err(rejected)?;
        json_of(&view)
    }

    fn job_cancel(&self, id: &str, agent: &str) -> PyResult<()> {
        self.hub.cancel(id, agent).map_err(rejected)
    }

    fn heal_json(&self) -> PyResult<String> {
        json_of(&self.hub.heal())
    }

    fn report_error(&self, component: &str, code: &str, context: &str) {
        self.hub.report(component, code, context);
    }

    #[staticmethod]
    fn typed_error(code: &str, tool: &str) -> PyResult<String> {
        json_of(&ToolError::from_code(code, tool))
    }

    fn release_quarantine(&self, id: &str) -> PyResult<()> {
        self.hub.release_quarantine(id).map_err(rejected)
    }

    fn quarantined(&self) -> Vec<String> {
        self.hub.quarantined()
    }

    fn shutdown(&self) {
        self.hub.shutdown();
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMcpEngine>()?;
    m.add("McpRejected", m.py().get_type::<McpRejected>())?;
    Ok(())
}
