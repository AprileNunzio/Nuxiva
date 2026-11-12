use crate::fabric::{AclPrivilege, FabricTable};
use crate::model::{MatterAttributeValue, MatterNode};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum InteractionStatus {
    Success = 0x00,
    Failure = 0x01,
    UnsupportedEndpoint = 0x7F,
    InvalidAction = 0x80,
    UnsupportedCommand = 0x81,
    UnsupportedAttribute = 0x86,
    ConstraintError = 0x87,
    UnsupportedWrite = 0x88,
    UnsupportedAccess = 0x7E,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum InteractionAction {
    Read {
        endpoint_id: u16,
        cluster_id: u32,
        attribute_id: u32,
    },
    Write {
        endpoint_id: u16,
        cluster_id: u32,
        attribute_id: u32,
        value: MatterAttributeValue,
    },
    Invoke {
        endpoint_id: u16,
        cluster_id: u32,
        command_id: u32,
        payload: Vec<u8>,
    },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InteractionRequest {
    pub fabric_index: u8,
    pub subject: u64,
    pub action: InteractionAction,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InteractionResponse {
    pub status: InteractionStatus,
    pub value: Option<MatterAttributeValue>,
}

impl InteractionResponse {
    pub fn success(value: Option<MatterAttributeValue>) -> Self {
        Self {
            status: InteractionStatus::Success,
            value,
        }
    }

    pub fn error(status: InteractionStatus) -> Self {
        Self {
            status,
            value: None,
        }
    }
}

pub fn dispatch_interaction(
    node: &mut MatterNode,
    fabric_table: &FabricTable,
    request: &InteractionRequest,
) -> InteractionResponse {
    match &request.action {
        InteractionAction::Read {
            endpoint_id,
            cluster_id,
            attribute_id,
        } => {
            if !fabric_table.check_permission(
                request.fabric_index,
                request.subject,
                *cluster_id,
                AclPrivilege::View,
            ) {
                return InteractionResponse::error(InteractionStatus::UnsupportedAccess);
            }
            let ep = match node.get_endpoint(*endpoint_id) {
                Some(e) => e,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedEndpoint),
            };
            let cl = match ep.get_cluster(*cluster_id) {
                Some(c) => c,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedAttribute),
            };
            let attr = match cl.get_attribute(*attribute_id) {
                Some(a) => a,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedAttribute),
            };
            InteractionResponse::success(Some(attr.value.clone()))
        }
        InteractionAction::Write {
            endpoint_id,
            cluster_id,
            attribute_id,
            value,
        } => {
            if !fabric_table.check_permission(
                request.fabric_index,
                request.subject,
                *cluster_id,
                AclPrivilege::Operate,
            ) {
                return InteractionResponse::error(InteractionStatus::UnsupportedAccess);
            }
            let ep = match node.get_endpoint_mut(*endpoint_id) {
                Some(e) => e,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedEndpoint),
            };
            let cl = match ep.get_cluster_mut(*cluster_id) {
                Some(c) => c,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedAttribute),
            };
            match cl.set_attribute_value(*attribute_id, value.clone()) {
                Ok(()) => InteractionResponse::success(None),
                Err("AttributeNotWritable") => {
                    InteractionResponse::error(InteractionStatus::UnsupportedWrite)
                }
                Err(_) => InteractionResponse::error(InteractionStatus::UnsupportedAttribute),
            }
        }
        InteractionAction::Invoke {
            endpoint_id,
            cluster_id,
            command_id,
            ..
        } => {
            if !fabric_table.check_permission(
                request.fabric_index,
                request.subject,
                *cluster_id,
                AclPrivilege::Operate,
            ) {
                return InteractionResponse::error(InteractionStatus::UnsupportedAccess);
            }
            let ep = match node.get_endpoint(*endpoint_id) {
                Some(e) => e,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedEndpoint),
            };
            let cl = match ep.get_cluster(*cluster_id) {
                Some(c) => c,
                None => return InteractionResponse::error(InteractionStatus::UnsupportedCommand),
            };
            if !cl.supported_commands.contains(command_id) {
                return InteractionResponse::error(InteractionStatus::UnsupportedCommand);
            }
            InteractionResponse::success(None)
        }
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
mod tests {
    use super::*;
    use crate::fabric::AccessControlEntry;
    use crate::model::{MatterCluster, MatterEndpoint};
    use crate::spec::*;

    #[test]
    fn test_interaction_dispatch_read_and_write() {
        let mut node = MatterNode::new(1, 0xFFF1, 0x8001, "1.6.1").with_endpoint(
            MatterEndpoint::new(1, DEVICE_TYPE_ON_OFF_LIGHT, "Light").with_cluster(
                MatterCluster::new(CLUSTER_ON_OFF, "OnOff").with_attribute(
                    ATTR_ON_OFF,
                    "OnOff",
                    MatterAttributeValue::Bool(false),
                    true,
                ),
            ),
        );

        let mut fabrics = FabricTable::new();
        fabrics.add_acl_entry(AccessControlEntry {
            fabric_index: 1,
            privilege: AclPrivilege::Admin,
            auth_mode: 1,
            subjects: vec![100],
            clusters: vec![CLUSTER_ON_OFF],
        });

        let req_read = InteractionRequest {
            fabric_index: 1,
            subject: 100,
            action: InteractionAction::Read {
                endpoint_id: 1,
                cluster_id: CLUSTER_ON_OFF,
                attribute_id: ATTR_ON_OFF,
            },
        };
        let resp = dispatch_interaction(&mut node, &fabrics, &req_read);
        assert_eq!(resp.status, InteractionStatus::Success);
        assert_eq!(resp.value, Some(MatterAttributeValue::Bool(false)));

        let req_write = InteractionRequest {
            fabric_index: 1,
            subject: 100,
            action: InteractionAction::Write {
                endpoint_id: 1,
                cluster_id: CLUSTER_ON_OFF,
                attribute_id: ATTR_ON_OFF,
                value: MatterAttributeValue::Bool(true),
            },
        };
        let resp_w = dispatch_interaction(&mut node, &fabrics, &req_write);
        assert_eq!(resp_w.status, InteractionStatus::Success);

        let resp_read2 = dispatch_interaction(&mut node, &fabrics, &req_read);
        assert_eq!(resp_read2.value, Some(MatterAttributeValue::Bool(true)));
    }
}
