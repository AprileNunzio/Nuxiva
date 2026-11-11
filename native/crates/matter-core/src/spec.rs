use serde::{Deserialize, Serialize};

pub const CLUSTER_BASIC_INFORMATION: u32 = 0x0028;
pub const CLUSTER_ACCESS_CONTROL: u32 = 0x001F;
pub const CLUSTER_GROUP_KEY_MANAGEMENT: u32 = 0x003F;
pub const CLUSTER_GENERAL_COMMISSIONING: u32 = 0x0030;
pub const CLUSTER_NETWORK_COMMISSIONING: u32 = 0x0031;
pub const CLUSTER_OPERATIONAL_CREDENTIALS: u32 = 0x003E;
pub const CLUSTER_ADMIN_COMMISSIONING: u32 = 0x003C;
pub const CLUSTER_TIME_SYNCHRONIZATION: u32 = 0x0038;

pub const CLUSTER_ON_OFF: u32 = 0x0006;
pub const CLUSTER_LEVEL_CONTROL: u32 = 0x0008;
pub const CLUSTER_COLOR_CONTROL: u32 = 0x0300;
pub const CLUSTER_WINDOW_COVERING: u32 = 0x0102;
pub const CLUSTER_DOOR_LOCK: u32 = 0x0101;

pub const CLUSTER_THERMOSTAT: u32 = 0x0201;
pub const CLUSTER_FAN_CONTROL: u32 = 0x0202;
pub const CLUSTER_TEMPERATURE_MEASUREMENT: u32 = 0x0402;
pub const CLUSTER_HUMIDITY_MEASUREMENT: u32 = 0x0405;
pub const CLUSTER_PRESSURE_MEASUREMENT: u32 = 0x0403;
pub const CLUSTER_ILLUMINANCE_MEASUREMENT: u32 = 0x0400;

pub const CLUSTER_OCCUPANCY_SENSING: u32 = 0x0406;
pub const CLUSTER_BOOLEAN_STATE: u32 = 0x0045;
pub const CLUSTER_SMOKE_CO_ALARM: u32 = 0x005C;
pub const CLUSTER_AIR_QUALITY: u32 = 0x005B;
pub const CLUSTER_WATER_FREEZE_DETECTOR: u32 = 0x0041;
pub const CLUSTER_WATER_VALVE: u32 = 0x0081;

pub const CLUSTER_ELECTRICAL_ENERGY_MEASUREMENT: u32 = 0x0091;
pub const CLUSTER_ELECTRICAL_POWER_MEASUREMENT: u32 = 0x0090;
pub const CLUSTER_DEVICE_ENERGY_MANAGEMENT: u32 = 0x0098;
pub const CLUSTER_ENERGY_EVSE: u32 = 0x0099;
pub const CLUSTER_BATTERY_STORAGE: u32 = 0x009B;
pub const CLUSTER_SOLAR_POWER: u32 = 0x009C;

pub const CLUSTER_MEDIA_PLAYBACK: u32 = 0x0506;
pub const CLUSTER_AUDIO_OUTPUT: u32 = 0x050B;
pub const CLUSTER_KEYPAD_INPUT: u32 = 0x0509;
pub const CLUSTER_CONTENT_LAUNCHER: u32 = 0x050A;

pub const CLUSTER_CAMERA_VIDEO_STREAM: u32 = 0x0550;
pub const CLUSTER_PUSH_TO_TALK_AUDIO: u32 = 0x0551;
pub const CLUSTER_PAN_TILT_ZOOM_CONTROL: u32 = 0x0552;

pub const ATTR_ON_OFF: u32 = 0x0000;
pub const ATTR_CURRENT_LEVEL: u32 = 0x0000;
pub const ATTR_LOCAL_TEMPERATURE: u32 = 0x0000;
pub const ATTR_MEASURED_VALUE: u32 = 0x0000;
pub const ATTR_OCCUPANCY: u32 = 0x0000;
pub const ATTR_STATE_VALUE: u32 = 0x0000;
pub const ATTR_LOCK_STATE: u32 = 0x0000;
pub const ATTR_ACTIVE_POWER: u32 = 0x0000;
pub const ATTR_CUMULATIVE_ENERGY: u32 = 0x0001;
pub const ATTR_ALARM_STATE: u32 = 0x0000;
pub const ATTR_PTZ_PAN: u32 = 0x0001;
pub const ATTR_PTZ_TILT: u32 = 0x0002;
pub const ATTR_PTZ_ZOOM: u32 = 0x0003;

pub const CMD_OFF: u32 = 0x0000;
pub const CMD_ON: u32 = 0x0001;
pub const CMD_TOGGLE: u32 = 0x0002;
pub const CMD_MOVE_TO_LEVEL: u32 = 0x0000;
pub const CMD_LOCK_DOOR: u32 = 0x0000;
pub const CMD_UNLOCK_DOOR: u32 = 0x0001;
pub const CMD_PTZ_MOVE: u32 = 0x0001;
pub const CMD_PTZ_STOP: u32 = 0x0002;
pub const CMD_EMERGENCY_ALARM: u32 = 0x0010;
pub const CMD_SILENCE_ALARM: u32 = 0x0011;

pub const DEVICE_TYPE_ROOT_NODE: u32 = 0x0016;
pub const DEVICE_TYPE_BRIDGED_NODE: u32 = 0x0013;
pub const DEVICE_TYPE_ON_OFF_LIGHT: u32 = 0x0100;
pub const DEVICE_TYPE_DIMMABLE_LIGHT: u32 = 0x0101;
pub const DEVICE_TYPE_COLOR_TEMPERATURE_LIGHT: u32 = 0x010C;
pub const DEVICE_TYPE_ON_OFF_PLUG: u32 = 0x010A;
pub const DEVICE_TYPE_THERMOSTAT: u32 = 0x0301;
pub const DEVICE_TYPE_TEMPERATURE_SENSOR: u32 = 0x0302;
pub const DEVICE_TYPE_OCCUPANCY_SENSOR: u32 = 0x0107;
pub const DEVICE_TYPE_CONTACT_SENSOR: u32 = 0x0015;
pub const DEVICE_TYPE_SMOKE_CO_ALARM: u32 = 0x0076;
pub const DEVICE_TYPE_SECURITY_CAMERA: u32 = 0x0500;
pub const DEVICE_TYPE_SMART_METER: u32 = 0x0510;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum MatterStandardVersion {
    V1_0,
    V1_1,
    V1_2,
    V1_3,
    V1_4,
    V1_5,
    #[default]
    V1_6_1,
}

pub fn cluster_name(cluster_id: u32) -> &'static str {
    match cluster_id {
        CLUSTER_BASIC_INFORMATION => "BasicInformation",
        CLUSTER_ACCESS_CONTROL => "AccessControl",
        CLUSTER_GROUP_KEY_MANAGEMENT => "GroupKeyManagement",
        CLUSTER_GENERAL_COMMISSIONING => "GeneralCommissioning",
        CLUSTER_NETWORK_COMMISSIONING => "NetworkCommissioning",
        CLUSTER_OPERATIONAL_CREDENTIALS => "OperationalCredentials",
        CLUSTER_ADMIN_COMMISSIONING => "AdminCommissioning",
        CLUSTER_TIME_SYNCHRONIZATION => "TimeSynchronization",
        CLUSTER_ON_OFF => "OnOff",
        CLUSTER_LEVEL_CONTROL => "LevelControl",
        CLUSTER_COLOR_CONTROL => "ColorControl",
        CLUSTER_WINDOW_COVERING => "WindowCovering",
        CLUSTER_DOOR_LOCK => "DoorLock",
        CLUSTER_THERMOSTAT => "Thermostat",
        CLUSTER_FAN_CONTROL => "FanControl",
        CLUSTER_TEMPERATURE_MEASUREMENT => "TemperatureMeasurement",
        CLUSTER_HUMIDITY_MEASUREMENT => "HumidityMeasurement",
        CLUSTER_PRESSURE_MEASUREMENT => "PressureMeasurement",
        CLUSTER_ILLUMINANCE_MEASUREMENT => "IlluminanceMeasurement",
        CLUSTER_OCCUPANCY_SENSING => "OccupancySensing",
        CLUSTER_BOOLEAN_STATE => "BooleanState",
        CLUSTER_SMOKE_CO_ALARM => "SmokeCOAlarm",
        CLUSTER_AIR_QUALITY => "AirQuality",
        CLUSTER_WATER_FREEZE_DETECTOR => "WaterFreezeDetector",
        CLUSTER_WATER_VALVE => "WaterValve",
        CLUSTER_ELECTRICAL_ENERGY_MEASUREMENT => "ElectricalEnergyMeasurement",
        CLUSTER_ELECTRICAL_POWER_MEASUREMENT => "ElectricalPowerMeasurement",
        CLUSTER_DEVICE_ENERGY_MANAGEMENT => "DeviceEnergyManagement",
        CLUSTER_ENERGY_EVSE => "EnergyEVSE",
        CLUSTER_BATTERY_STORAGE => "BatteryStorage",
        CLUSTER_SOLAR_POWER => "SolarPower",
        CLUSTER_MEDIA_PLAYBACK => "MediaPlayback",
        CLUSTER_AUDIO_OUTPUT => "AudioOutput",
        CLUSTER_KEYPAD_INPUT => "KeypadInput",
        CLUSTER_CONTENT_LAUNCHER => "ContentLauncher",
        CLUSTER_CAMERA_VIDEO_STREAM => "CameraVideoStream",
        CLUSTER_PUSH_TO_TALK_AUDIO => "PushToTalkAudio",
        CLUSTER_PAN_TILT_ZOOM_CONTROL => "PanTiltZoomControl",
        _ => "UnknownCluster",
    }
}
