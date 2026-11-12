from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

class MatterStandardVersion(str, Enum):
    V1_0 = "1.0"
    V1_1 = "1.1"
    V1_2 = "1.2"
    V1_3 = "1.3"
    V1_4 = "1.4"
    V1_5 = "1.5"
    V1_6_1 = "1.6.1"

class MatterDeviceType(int, Enum):
    ROOT_NODE = 0x0016
    BRIDGED_NODE = 0x0013
    ON_OFF_LIGHT = 0x0100
    DIMMABLE_LIGHT = 0x0101
    COLOR_TEMPERATURE_LIGHT = 0x010C
    ON_OFF_PLUG = 0x010A
    THERMOSTAT = 0x0301
    TEMPERATURE_SENSOR = 0x0302
    OCCUPANCY_SENSOR = 0x0107
    CONTACT_SENSOR = 0x0015
    SMOKE_CO_ALARM = 0x0076
    SECURITY_CAMERA = 0x0500
    SMART_METER = 0x0510

class MatterClusterId(int, Enum):
    BASIC_INFORMATION = 0x0028
    ACCESS_CONTROL = 0x001F
    GROUP_KEY_MANAGEMENT = 0x003F
    GENERAL_COMMISSIONING = 0x0030
    NETWORK_COMMISSIONING = 0x0031
    OPERATIONAL_CREDENTIALS = 0x003E
    ADMIN_COMMISSIONING = 0x003C
    TIME_SYNCHRONIZATION = 0x0038
    ON_OFF = 0x0006
    LEVEL_CONTROL = 0x0008
    COLOR_CONTROL = 0x0300
    WINDOW_COVERING = 0x0102
    DOOR_LOCK = 0x0101
    THERMOSTAT = 0x0201
    FAN_CONTROL = 0x0202
    TEMPERATURE_MEASUREMENT = 0x0402
    HUMIDITY_MEASUREMENT = 0x0405
    PRESSURE_MEASUREMENT = 0x0403
    ILLUMINANCE_MEASUREMENT = 0x0400
    OCCUPANCY_SENSING = 0x0406
    BOOLEAN_STATE = 0x0045
    SMOKE_CO_ALARM = 0x005C
    AIR_QUALITY = 0x005B
    WATER_FREEZE_DETECTOR = 0x0041
    WATER_VALVE = 0x0081
    ELECTRICAL_ENERGY_MEASUREMENT = 0x0091
    ELECTRICAL_POWER_MEASUREMENT = 0x0090
    DEVICE_ENERGY_MANAGEMENT = 0x0098
    ENERGY_EVSE = 0x0099
    BATTERY_STORAGE = 0x009B
    SOLAR_POWER = 0x009C
    MEDIA_PLAYBACK = 0x0506
    AUDIO_OUTPUT = 0x050B
    KEYPAD_INPUT = 0x0509
    CONTENT_LAUNCHER = 0x050A
    CAMERA_VIDEO_STREAM = 0x0550
    PUSH_TO_TALK_AUDIO = 0x0551
    PAN_TILT_ZOOM_CONTROL = 0x0552

class MatterCommandId(int, Enum):
    OFF = 0x0000
    ON = 0x0001
    TOGGLE = 0x0002
    MOVE_TO_LEVEL = 0x0000
    LOCK_DOOR = 0x0000
    UNLOCK_DOOR = 0x0001
    PTZ_MOVE = 0x0001
    PTZ_STOP = 0x0002
    EMERGENCY_ALARM = 0x0010
    SILENCE_ALARM = 0x0011

@dataclass
class MatterAttributeModel:
    id: int
    name: str
    value: Any
    writable: bool = False

@dataclass
class MatterClusterModel:
    id: int
    name: str
    attributes: Dict[int, MatterAttributeModel] = field(default_factory=dict)
    supported_commands: List[int] = field(default_factory=list)

@dataclass
class MatterEndpointModel:
    id: int
    device_type: int
    name: str
    clusters: Dict[int, MatterClusterModel] = field(default_factory=dict)

@dataclass
class MatterNodeModel:
    node_id: int
    vendor_id: int
    product_id: int
    version: str = "1.6.1"
    name: str = ""
    connected: bool = True
    endpoints: Dict[int, MatterEndpointModel] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
