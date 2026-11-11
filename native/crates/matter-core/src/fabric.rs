use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum AclPrivilege {
    View,
    Operate,
    Manage,
    Admin,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AccessControlEntry {
    pub fabric_index: u8,
    pub privilege: AclPrivilege,
    pub auth_mode: u8,
    pub subjects: Vec<u64>,
    pub clusters: Vec<u32>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MatterFabric {
    pub fabric_id: u64,
    pub node_id: u64,
    pub vendor_id: u16,
    pub fabric_index: u8,
    pub label: String,
    pub root_public_key: Vec<u8>,
}

impl MatterFabric {
    pub fn new(
        fabric_id: u64,
        node_id: u64,
        vendor_id: u16,
        fabric_index: u8,
        label: impl Into<String>,
        root_public_key: Vec<u8>,
    ) -> Self {
        Self {
            fabric_id,
            node_id,
            vendor_id,
            fabric_index,
            label: label.into(),
            root_public_key,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FabricTable {
    pub fabrics: Vec<MatterFabric>,
    pub active_index: u8,
    pub acl: Vec<AccessControlEntry>,
}

impl Default for FabricTable {
    fn default() -> Self {
        Self::new()
    }
}

impl FabricTable {
    pub fn new() -> Self {
        Self {
            fabrics: Vec::new(),
            active_index: 0,
            acl: Vec::new(),
        }
    }

    pub fn add_fabric(&mut self, fabric: MatterFabric) -> Result<u8, &'static str> {
        if self.fabrics.len() >= 16 {
            return Err("FabricTableFull");
        }
        let index = fabric.fabric_index;
        if self.fabrics.iter().any(|f| f.fabric_index == index) {
            return Err("FabricIndexAlreadyExists");
        }
        self.fabrics.push(fabric);
        if self.active_index == 0 {
            self.active_index = index;
        }
        Ok(index)
    }

    pub fn remove_fabric(&mut self, fabric_index: u8) -> Result<(), &'static str> {
        let initial_len = self.fabrics.len();
        self.fabrics.retain(|f| f.fabric_index != fabric_index);
        if self.fabrics.len() == initial_len {
            return Err("FabricNotFound");
        }
        self.acl.retain(|a| a.fabric_index != fabric_index);
        if self.active_index == fabric_index {
            self.active_index = self.fabrics.first().map_or(0, |f| f.fabric_index);
        }
        Ok(())
    }

    pub fn get_fabric(&self, fabric_index: u8) -> Option<&MatterFabric> {
        self.fabrics.iter().find(|f| f.fabric_index == fabric_index)
    }

    pub fn add_acl_entry(&mut self, entry: AccessControlEntry) {
        self.acl.push(entry);
    }

    pub fn check_permission(
        &self,
        fabric_index: u8,
        subject: u64,
        cluster_id: u32,
        required: AclPrivilege,
    ) -> bool {
        self.acl.iter().any(|entry| {
            if entry.fabric_index != fabric_index {
                return false;
            }
            if !entry.subjects.is_empty() && !entry.subjects.contains(&subject) {
                return false;
            }
            if !entry.clusters.is_empty() && !entry.clusters.contains(&cluster_id) {
                return false;
            }
            entry.privilege >= required
        })
    }
}
