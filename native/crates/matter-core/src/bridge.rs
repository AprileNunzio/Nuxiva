use crate::model::{MatterAttributeValue, MatterCluster, MatterEndpoint, MatterNode};
use crate::spec::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum BridgedDeviceKind {
    OnOffLight,
    DimmableLight,
    Thermostat,
    TemperatureSensor,
    OccupancySensor,
    ContactSensor,
    SmokeCoAlarm,
    SecurityCameraPtz,
    SmartEnergyMeter,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BridgedEntity {
    pub entity_id: String,
    pub endpoint_id: u16,
    pub kind: BridgedDeviceKind,
    pub label: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MatterBridge {
    pub node: MatterNode,
    pub entities: Vec<BridgedEntity>,
    next_endpoint_id: u16,
}

impl Default for MatterBridge {
    fn default() -> Self {
        Self::new(0x1122334455667788, 0xFFF1, 0x8001)
    }
}

impl MatterBridge {
    pub fn new(node_id: u64, vendor_id: u16, product_id: u16) -> Self {
        let root_ep = MatterEndpoint::new(0, DEVICE_TYPE_ROOT_NODE, "Root")
            .with_cluster(
                MatterCluster::new(CLUSTER_BASIC_INFORMATION, "BasicInformation")
                    .with_attribute(
                        0x0001,
                        "VendorName",
                        MatterAttributeValue::String("Nuxiva".to_string()),
                        false,
                    )
                    .with_attribute(
                        0x0002,
                        "VendorID",
                        MatterAttributeValue::Uint(vendor_id as u64),
                        false,
                    )
                    .with_attribute(
                        0x0003,
                        "ProductName",
                        MatterAttributeValue::String("Nuxiva Universal Bridge 1.6.1".to_string()),
                        false,
                    )
                    .with_attribute(
                        0x0004,
                        "ProductID",
                        MatterAttributeValue::Uint(product_id as u64),
                        false,
                    ),
            )
            .with_cluster(MatterCluster::new(CLUSTER_ACCESS_CONTROL, "AccessControl"));

        let node = MatterNode::new(node_id, vendor_id, product_id, "1.6.1").with_endpoint(root_ep);

        Self {
            node,
            entities: Vec::new(),
            next_endpoint_id: 1,
        }
    }

    pub fn bridge_entity(
        &mut self,
        entity_id: impl Into<String>,
        kind: BridgedDeviceKind,
        label: impl Into<String>,
    ) -> u16 {
        let id_str = entity_id.into();
        let label_str = label.into();

        if let Some(existing) = self.entities.iter().find(|e| e.entity_id == id_str) {
            return existing.endpoint_id;
        }

        let ep_id = self.next_endpoint_id;
        self.next_endpoint_id = self.next_endpoint_id.saturating_add(1);

        let ep = match kind {
            BridgedDeviceKind::OnOffLight => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_ON_OFF_LIGHT, &label_str).with_cluster(
                    MatterCluster::new(CLUSTER_ON_OFF, "OnOff")
                        .with_attribute(
                            ATTR_ON_OFF,
                            "OnOff",
                            MatterAttributeValue::Bool(false),
                            true,
                        )
                        .with_command(CMD_OFF)
                        .with_command(CMD_ON)
                        .with_command(CMD_TOGGLE),
                )
            }
            BridgedDeviceKind::DimmableLight => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_DIMMABLE_LIGHT, &label_str)
                    .with_cluster(
                        MatterCluster::new(CLUSTER_ON_OFF, "OnOff")
                            .with_attribute(
                                ATTR_ON_OFF,
                                "OnOff",
                                MatterAttributeValue::Bool(false),
                                true,
                            )
                            .with_command(CMD_OFF)
                            .with_command(CMD_ON)
                            .with_command(CMD_TOGGLE),
                    )
                    .with_cluster(
                        MatterCluster::new(CLUSTER_LEVEL_CONTROL, "LevelControl")
                            .with_attribute(
                                ATTR_CURRENT_LEVEL,
                                "CurrentLevel",
                                MatterAttributeValue::Uint(254),
                                true,
                            )
                            .with_command(CMD_MOVE_TO_LEVEL),
                    )
            }
            BridgedDeviceKind::Thermostat => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_THERMOSTAT, &label_str).with_cluster(
                    MatterCluster::new(CLUSTER_THERMOSTAT, "Thermostat").with_attribute(
                        ATTR_LOCAL_TEMPERATURE,
                        "LocalTemperature",
                        MatterAttributeValue::Int(2100),
                        false,
                    ),
                )
            }
            BridgedDeviceKind::TemperatureSensor => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_TEMPERATURE_SENSOR, &label_str).with_cluster(
                    MatterCluster::new(CLUSTER_TEMPERATURE_MEASUREMENT, "TemperatureMeasurement")
                        .with_attribute(
                            ATTR_MEASURED_VALUE,
                            "MeasuredValue",
                            MatterAttributeValue::Int(2050),
                            false,
                        ),
                )
            }
            BridgedDeviceKind::OccupancySensor => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_OCCUPANCY_SENSOR, &label_str).with_cluster(
                    MatterCluster::new(CLUSTER_OCCUPANCY_SENSING, "OccupancySensing")
                        .with_attribute(
                            ATTR_OCCUPANCY,
                            "Occupancy",
                            MatterAttributeValue::Uint(0),
                            false,
                        ),
                )
            }
            BridgedDeviceKind::ContactSensor => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_CONTACT_SENSOR, &label_str).with_cluster(
                    MatterCluster::new(CLUSTER_BOOLEAN_STATE, "BooleanState").with_attribute(
                        ATTR_STATE_VALUE,
                        "StateValue",
                        MatterAttributeValue::Bool(false),
                        false,
                    ),
                )
            }
            BridgedDeviceKind::SmokeCoAlarm => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_SMOKE_CO_ALARM, &label_str).with_cluster(
                    MatterCluster::new(CLUSTER_SMOKE_CO_ALARM, "SmokeCOAlarm")
                        .with_attribute(
                            ATTR_ALARM_STATE,
                            "AlarmState",
                            MatterAttributeValue::Uint(0),
                            false,
                        )
                        .with_command(CMD_EMERGENCY_ALARM)
                        .with_command(CMD_SILENCE_ALARM),
                )
            }
            BridgedDeviceKind::SecurityCameraPtz => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_SECURITY_CAMERA, &label_str)
                    .with_cluster(
                        MatterCluster::new(CLUSTER_CAMERA_VIDEO_STREAM, "CameraVideoStream")
                            .with_attribute(
                                0x0001,
                                "StreamActive",
                                MatterAttributeValue::Bool(true),
                                false,
                            ),
                    )
                    .with_cluster(
                        MatterCluster::new(CLUSTER_PAN_TILT_ZOOM_CONTROL, "PanTiltZoomControl")
                            .with_attribute(
                                ATTR_PTZ_PAN,
                                "Pan",
                                MatterAttributeValue::Float(0.0),
                                true,
                            )
                            .with_attribute(
                                ATTR_PTZ_TILT,
                                "Tilt",
                                MatterAttributeValue::Float(0.0),
                                true,
                            )
                            .with_attribute(
                                ATTR_PTZ_ZOOM,
                                "Zoom",
                                MatterAttributeValue::Float(1.0),
                                true,
                            )
                            .with_command(CMD_PTZ_MOVE)
                            .with_command(CMD_PTZ_STOP),
                    )
            }
            BridgedDeviceKind::SmartEnergyMeter => {
                MatterEndpoint::new(ep_id, DEVICE_TYPE_SMART_METER, &label_str)
                    .with_cluster(
                        MatterCluster::new(
                            CLUSTER_ELECTRICAL_POWER_MEASUREMENT,
                            "ElectricalPowerMeasurement",
                        )
                        .with_attribute(
                            ATTR_ACTIVE_POWER,
                            "ActivePower",
                            MatterAttributeValue::Int(0),
                            false,
                        ),
                    )
                    .with_cluster(
                        MatterCluster::new(
                            CLUSTER_ELECTRICAL_ENERGY_MEASUREMENT,
                            "ElectricalEnergyMeasurement",
                        )
                        .with_attribute(
                            ATTR_CUMULATIVE_ENERGY,
                            "CumulativeEnergy",
                            MatterAttributeValue::Uint(0),
                            false,
                        ),
                    )
            }
        };

        self.node.endpoints.push(ep);
        self.entities.push(BridgedEntity {
            entity_id: id_str,
            endpoint_id: ep_id,
            kind,
            label: label_str,
        });

        ep_id
    }

    pub fn update_entity_state(
        &mut self,
        entity_id: &str,
        cluster_id: u32,
        attr_id: u32,
        value: MatterAttributeValue,
    ) -> Result<(), &'static str> {
        let entry = self
            .entities
            .iter()
            .find(|e| e.entity_id == entity_id)
            .ok_or("EntityNotFound")?;
        let ep_id = entry.endpoint_id;
        let ep = self
            .node
            .get_endpoint_mut(ep_id)
            .ok_or("EndpointNotFound")?;
        let cl = ep.get_cluster_mut(cluster_id).ok_or("ClusterNotFound")?;
        let attr = cl
            .attributes
            .iter_mut()
            .find(|a| a.id == attr_id)
            .ok_or("AttributeNotFound")?;
        attr.value = value;
        Ok(())
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
mod tests {
    use super::*;

    #[test]
    fn test_matter_bridge_entity_lifecycle() {
        let mut bridge = MatterBridge::default();
        let ep1 = bridge.bridge_entity(
            "light.living_room",
            BridgedDeviceKind::OnOffLight,
            "Salotto",
        );
        assert_eq!(ep1, 1);

        let ep2 = bridge.bridge_entity(
            "camera.garden_ptz",
            BridgedDeviceKind::SecurityCameraPtz,
            "Giardino PTZ",
        );
        assert_eq!(ep2, 2);

        let res = bridge.update_entity_state(
            "light.living_room",
            CLUSTER_ON_OFF,
            ATTR_ON_OFF,
            MatterAttributeValue::Bool(true),
        );
        assert!(res.is_ok());

        let val = bridge
            .node
            .read_attribute(1, CLUSTER_ON_OFF, ATTR_ON_OFF)
            .unwrap();
        assert_eq!(val, MatterAttributeValue::Bool(true));
    }
}
