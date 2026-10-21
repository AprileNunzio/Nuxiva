from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from server.features.repair_workbench.text_types import (
    MediumText,
    PinNumber,
    Reference,
    ShortText,
)


class ComponentCategory(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    LED = "led"
    TRANSISTOR = "transistor"
    MOSFET = "mosfet"
    IC = "ic"
    REGULATOR = "regulator"
    OPAMP = "opamp"
    MICROCONTROLLER = "microcontroller"
    CONNECTOR = "connector"
    CRYSTAL = "crystal"
    RELAY = "relay"
    TRANSFORMER = "transformer"
    FUSE = "fuse"
    SWITCH = "switch"
    SENSOR = "sensor"
    VOLTAGE_SOURCE = "voltage_source"
    CURRENT_SOURCE = "current_source"
    OTHER = "other"


class PinSpec(BaseModel):
    number: PinNumber
    name: ShortText = ""
    electrical_type: ShortText = "passive"


class ComponentSpec(BaseModel):
    ref: Reference
    value: ShortText = ""
    category: ComponentCategory = ComponentCategory.OTHER
    package: ShortText = ""
    description: MediumText = ""
    pins: List[PinSpec] = Field(default_factory=list, max_length=256)


class PinRef(BaseModel):
    ref: Reference
    pin: PinNumber


class NetSpec(BaseModel):
    name: ShortText
    connections: List[PinRef] = Field(default_factory=list, max_length=512)


class CircuitSpec(BaseModel):
    name: ShortText = ""
    description: MediumText = ""
    components: List[ComponentSpec] = Field(default_factory=list, max_length=1024)
    nets: List[NetSpec] = Field(default_factory=list, max_length=1024)

    def get_component(self, ref: str) -> Optional[ComponentSpec]:
        return next((c for c in self.components if c.ref == ref), None)

    def get_net(self, name: str) -> Optional[NetSpec]:
        return next((n for n in self.nets if n.name == name), None)
