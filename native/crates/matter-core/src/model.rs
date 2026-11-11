use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum MatterAttributeValue {
    Null,
    Bool(bool),
    Int(i64),
    Uint(u64),
    Float(f64),
    String(String),
    Bytes(Vec<u8>),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MatterAttribute {
    pub id: u32,
    pub name: String,
    pub value: MatterAttributeValue,
    pub writable: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MatterCluster {
    pub id: u32,
    pub name: String,
    pub attributes: Vec<MatterAttribute>,
    pub supported_commands: Vec<u32>,
}

impl MatterCluster {
    pub fn new(id: u32, name: impl Into<String>) -> Self {
        Self {
            id,
            name: name.into(),
            attributes: Vec::new(),
            supported_commands: Vec::new(),
        }
    }

    pub fn with_attribute(
        mut self,
        id: u32,
        name: impl Into<String>,
        value: MatterAttributeValue,
        writable: bool,
    ) -> Self {
        self.attributes.push(MatterAttribute {
            id,
            name: name.into(),
            value,
            writable,
        });
        self
    }

    pub fn with_command(mut self, cmd_id: u32) -> Self {
        self.supported_commands.push(cmd_id);
        self
    }

    pub fn get_attribute(&self, attr_id: u32) -> Option<&MatterAttribute> {
        self.attributes.iter().find(|a| a.id == attr_id)
    }

    pub fn set_attribute_value(
        &mut self,
        attr_id: u32,
        value: MatterAttributeValue,
    ) -> Result<(), &'static str> {
        let attr = self
            .attributes
            .iter_mut()
            .find(|a| a.id == attr_id)
            .ok_or("AttributeNotFound")?;
        if !attr.writable {
            return Err("AttributeNotWritable");
        }
        attr.value = value;
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MatterEndpoint {
    pub id: u16,
    pub device_type: u32,
    pub name: String,
    pub clusters: Vec<MatterCluster>,
}

impl MatterEndpoint {
    pub fn new(id: u16, device_type: u32, name: impl Into<String>) -> Self {
        Self {
            id,
            device_type,
            name: name.into(),
            clusters: Vec::new(),
        }
    }

    pub fn with_cluster(mut self, cluster: MatterCluster) -> Self {
        self.clusters.push(cluster);
        self
    }

    pub fn get_cluster(&self, cluster_id: u32) -> Option<&MatterCluster> {
        self.clusters.iter().find(|c| c.id == cluster_id)
    }

    pub fn get_cluster_mut(&mut self, cluster_id: u32) -> Option<&mut MatterCluster> {
        self.clusters.iter_mut().find(|c| c.id == cluster_id)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MatterNode {
    pub node_id: u64,
    pub vendor_id: u16,
    pub product_id: u16,
    pub version: String,
    pub endpoints: Vec<MatterEndpoint>,
}

impl MatterNode {
    pub fn new(node_id: u64, vendor_id: u16, product_id: u16, version: impl Into<String>) -> Self {
        Self {
            node_id,
            vendor_id,
            product_id,
            version: version.into(),
            endpoints: Vec::new(),
        }
    }

    pub fn with_endpoint(mut self, endpoint: MatterEndpoint) -> Self {
        self.endpoints.push(endpoint);
        self
    }

    pub fn get_endpoint(&self, ep_id: u16) -> Option<&MatterEndpoint> {
        self.endpoints.iter().find(|e| e.id == ep_id)
    }

    pub fn get_endpoint_mut(&mut self, ep_id: u16) -> Option<&mut MatterEndpoint> {
        self.endpoints.iter_mut().find(|e| e.id == ep_id)
    }

    pub fn read_attribute(
        &self,
        ep_id: u16,
        cluster_id: u32,
        attr_id: u32,
    ) -> Result<MatterAttributeValue, &'static str> {
        let ep = self.get_endpoint(ep_id).ok_or("EndpointNotFound")?;
        let cluster = ep.get_cluster(cluster_id).ok_or("ClusterNotFound")?;
        let attr = cluster.get_attribute(attr_id).ok_or("AttributeNotFound")?;
        Ok(attr.value.clone())
    }

    pub fn write_attribute(
        &mut self,
        ep_id: u16,
        cluster_id: u32,
        attr_id: u32,
        value: MatterAttributeValue,
    ) -> Result<(), &'static str> {
        let ep = self.get_endpoint_mut(ep_id).ok_or("EndpointNotFound")?;
        let cluster = ep.get_cluster_mut(cluster_id).ok_or("ClusterNotFound")?;
        cluster.set_attribute_value(attr_id, value)
    }
}
