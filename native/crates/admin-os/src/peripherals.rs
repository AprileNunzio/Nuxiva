use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeviceKind {
    Camera,
    AudioInput,
    AudioOutput,
    Printer,
    BluetoothDevice,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PeripheralDevice {
    pub id: String,
    pub name: String,
    pub kind: DeviceKind,
    pub connected: bool,
    pub busy: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StorePackageMeta {
    pub id: String,
    pub name: String,
    pub version: String,
    pub installed: bool,
    pub size_bytes: u64,
    pub category: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PeripheralsSummary {
    pub total_devices: usize,
    pub connected_devices: usize,
    pub busy_devices: usize,
    pub installed_packages: usize,
}

#[derive(Debug, Clone, Default)]
pub struct PeripheralsManager {
    devices: Vec<PeripheralDevice>,
    packages: Vec<StorePackageMeta>,
}

impl PeripheralsManager {
    #[must_use]
    pub fn new() -> Self {
        Self {
            devices: Vec::new(),
            packages: Vec::new(),
        }
    }

    pub fn register_device(&mut self, device: PeripheralDevice) {
        if let Some(pos) = self.devices.iter().position(|d| d.id == device.id) {
            if let Some(existing) = self.devices.get_mut(pos) {
                *existing = device;
            }
        } else {
            self.devices.push(device);
        }
    }

    pub fn set_device_status(&mut self, id: &str, connected: bool, busy: bool) -> bool {
        if let Some(dev) = self.devices.iter_mut().find(|d| d.id == id) {
            dev.connected = connected;
            dev.busy = busy;
            true
        } else {
            false
        }
    }

    pub fn remove_device(&mut self, id: &str) -> bool {
        let initial_len = self.devices.len();
        self.devices.retain(|d| d.id != id);
        self.devices.len() < initial_len
    }

    pub fn register_package(&mut self, package: StorePackageMeta) {
        if let Some(pos) = self.packages.iter().position(|p| p.id == package.id) {
            if let Some(existing) = self.packages.get_mut(pos) {
                *existing = package;
            }
        } else {
            self.packages.push(package);
        }
    }

    pub fn set_package_installed(&mut self, id: &str, installed: bool) -> bool {
        if let Some(pkg) = self.packages.iter_mut().find(|p| p.id == id) {
            pkg.installed = installed;
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn get_devices_by_kind(&self, kind: DeviceKind) -> Vec<&PeripheralDevice> {
        self.devices.iter().filter(|d| d.kind == kind).collect()
    }

    #[must_use]
    pub fn get_devices(&self) -> &[PeripheralDevice] {
        &self.devices
    }

    #[must_use]
    pub fn get_packages(&self) -> &[StorePackageMeta] {
        &self.packages
    }

    #[must_use]
    pub fn summary(&self) -> PeripheralsSummary {
        let connected_devices = self.devices.iter().filter(|d| d.connected).count();
        let busy_devices = self.devices.iter().filter(|d| d.busy).count();
        let installed_packages = self.packages.iter().filter(|p| p.installed).count();

        PeripheralsSummary {
            total_devices: self.devices.len(),
            connected_devices,
            busy_devices,
            installed_packages,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_device_lifecycle() {
        let mut mgr = PeripheralsManager::new();
        let cam = PeripheralDevice {
            id: "cam-front".to_string(),
            name: "Front Webcam".to_string(),
            kind: DeviceKind::Camera,
            connected: true,
            busy: false,
        };

        mgr.register_device(cam);
        assert_eq!(mgr.get_devices().len(), 1);
        assert_eq!(mgr.get_devices_by_kind(DeviceKind::Camera).len(), 1);
        assert_eq!(mgr.get_devices_by_kind(DeviceKind::Printer).len(), 0);

        assert!(mgr.set_device_status("cam-front", true, true));
        assert!(mgr.get_devices().first().is_some_and(|d| d.busy));

        assert!(mgr.remove_device("cam-front"));
        assert_eq!(mgr.get_devices().len(), 0);
    }

    #[test]
    fn test_packages_management() {
        let mut mgr = PeripheralsManager::new();
        let pkg = StorePackageMeta {
            id: "nuxiva-vision".to_string(),
            name: "Vision Suite".to_string(),
            version: "1.0.0".to_string(),
            installed: false,
            size_bytes: 50_000_000,
            category: "ai".to_string(),
        };

        mgr.register_package(pkg);
        assert_eq!(mgr.get_packages().len(), 1);

        assert!(mgr.set_package_installed("nuxiva-vision", true));
        assert!(mgr.get_packages().first().is_some_and(|p| p.installed));

        let summary = mgr.summary();
        assert_eq!(summary.installed_packages, 1);
        assert_eq!(summary.total_devices, 0);
    }
}
