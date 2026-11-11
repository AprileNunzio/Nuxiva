use nuxiva_matter_core::{
    BridgedDeviceKind, FabricTable, InteractionRequest, MatterAttributeValue, MatterBridge,
    MatterStandardVersion, TlvElement, decode_tlv, dispatch_interaction, encode_tlv,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

fn bad_arg<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn err_rt<E: std::fmt::Display>(e: E) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

#[derive(Debug, Serialize, Deserialize)]
struct SpecInfo {
    version: MatterStandardVersion,
    standard: &'static str,
    release: &'static str,
}

#[pyfunction]
fn matter_spec_info() -> PyResult<String> {
    let info = SpecInfo {
        version: MatterStandardVersion::V1_6_1,
        standard: "Matter 1.6.1 (CSA)",
        release: "2026-11",
    };
    serde_json::to_string(&info).map_err(err_rt)
}

#[pyfunction]
fn matter_tlv_to_json(tlv_bytes: &[u8]) -> PyResult<String> {
    let element = decode_tlv(tlv_bytes).map_err(bad_arg)?;
    serde_json::to_string(&element).map_err(err_rt)
}

#[pyfunction]
fn matter_json_to_tlv(json_str: &str) -> PyResult<Vec<u8>> {
    let element: TlvElement = serde_json::from_str(json_str).map_err(bad_arg)?;
    Ok(encode_tlv(&element))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustMatterBridge {
    bridge: MatterBridge,
    fabrics: FabricTable,
}

#[pymethods]
impl RustMatterBridge {
    #[new]
    pub fn new(node_id: u64, vendor_id: u16, product_id: u16) -> Self {
        Self {
            bridge: MatterBridge::new(node_id, vendor_id, product_id),
            fabrics: FabricTable::new(),
        }
    }

    pub fn bridge_entity(&mut self, entity_id: &str, kind_str: &str, label: &str) -> PyResult<u16> {
        let kind = match kind_str {
            "on_off_light" => BridgedDeviceKind::OnOffLight,
            "dimmable_light" => BridgedDeviceKind::DimmableLight,
            "thermostat" => BridgedDeviceKind::Thermostat,
            "temperature_sensor" => BridgedDeviceKind::TemperatureSensor,
            "occupancy_sensor" => BridgedDeviceKind::OccupancySensor,
            "contact_sensor" => BridgedDeviceKind::ContactSensor,
            "smoke_co_alarm" => BridgedDeviceKind::SmokeCoAlarm,
            "security_camera_ptz" => BridgedDeviceKind::SecurityCameraPtz,
            "smart_energy_meter" => BridgedDeviceKind::SmartEnergyMeter,
            _ => return Err(PyValueError::new_err("Unknown bridged device kind")),
        };
        Ok(self.bridge.bridge_entity(entity_id, kind, label))
    }

    pub fn update_entity_state(
        &mut self,
        entity_id: &str,
        cluster_id: u32,
        attr_id: u32,
        value_json: &str,
    ) -> PyResult<()> {
        let val: MatterAttributeValue = serde_json::from_str(value_json).map_err(bad_arg)?;
        self.bridge
            .update_entity_state(entity_id, cluster_id, attr_id, val)
            .map_err(bad_arg)
    }

    pub fn read_attribute(
        &self,
        endpoint_id: u16,
        cluster_id: u32,
        attr_id: u32,
    ) -> PyResult<String> {
        let val = self
            .bridge
            .node
            .read_attribute(endpoint_id, cluster_id, attr_id)
            .map_err(bad_arg)?;
        serde_json::to_string(&val).map_err(err_rt)
    }

    pub fn dispatch_interaction(&mut self, request_json: &str) -> PyResult<String> {
        let req: InteractionRequest = serde_json::from_str(request_json).map_err(bad_arg)?;
        let resp = dispatch_interaction(&mut self.bridge.node, &self.fabrics, &req);
        serde_json::to_string(&resp).map_err(err_rt)
    }

    pub fn dump_state(&self) -> PyResult<String> {
        serde_json::to_string(&self.bridge).map_err(err_rt)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMatterBridge>()?;
    m.add_function(wrap_pyfunction!(matter_spec_info, m)?)?;
    m.add_function(wrap_pyfunction!(matter_tlv_to_json, m)?)?;
    m.add_function(wrap_pyfunction!(matter_json_to_tlv, m)?)?;
    Ok(())
}
