from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from server.features.repair_workbench.circuit_schemas import (
    CircuitSpec,
    ComponentCategory,
)
from server.features.repair_workbench.value_parser import parse_value

GROUND_NAMES = {"gnd", "0", "vss", "agnd", "dgnd"}

LINEAR_KINDS = {
    ComponentCategory.RESISTOR: "R",
    ComponentCategory.CAPACITOR: "C",
    ComponentCategory.INDUCTOR: "L",
    ComponentCategory.VOLTAGE_SOURCE: "V",
    ComponentCategory.CURRENT_SOURCE: "I",
}


@dataclass(frozen=True)
class Element:
    ref: str
    kind: str
    node_a: Optional[str]
    node_b: Optional[str]
    value: float


@dataclass(frozen=True)
class ExtractedNetwork:
    elements: List[Element]
    nodes: List[str]
    unsupported: List[str]
    pin_nets: Dict[Tuple[str, str], str]


def is_ground(name: str) -> bool:
    return name.strip().lower() in GROUND_NAMES


def _pin_nets(circuit: CircuitSpec) -> Dict[Tuple[str, str], str]:
    mapping: Dict[Tuple[str, str], str] = {}
    for net in circuit.nets:
        for connection in net.connections:
            mapping.setdefault((connection.ref, connection.pin), net.name)
    return mapping


def _terminals(component, pin_nets) -> Optional[Tuple[Optional[str], Optional[str]]]:
    numbers = [p.number for p in component.pins[:2]] or ["1", "2"]
    if len(numbers) < 2:
        return None
    first = pin_nets.get((component.ref, numbers[0]))
    second = pin_nets.get((component.ref, numbers[1]))
    if first is None or second is None:
        return None
    return (None if is_ground(first) else first, None if is_ground(second) else second)


def extract_network(circuit: CircuitSpec) -> ExtractedNetwork:
    pin_nets = _pin_nets(circuit)
    elements: List[Element] = []
    unsupported: List[str] = []
    seen_pins: Dict[Tuple[str, str], str] = {}
    for net in circuit.nets:
        for connection in net.connections:
            key = (connection.ref, connection.pin)
            previous = seen_pins.setdefault(key, net.name)
            if previous != net.name:
                unsupported.append(connection.ref)
    for component in circuit.components:
        kind = LINEAR_KINDS.get(component.category)
        if kind is None:
            if any(key[0] == component.ref for key in pin_nets):
                unsupported.append(component.ref)
            continue
        value = parse_value(component.value)
        terminals = _terminals(component, pin_nets)
        if value is None or terminals is None or (kind in "RCL" and value <= 0):
            unsupported.append(component.ref)
            continue
        elements.append(Element(component.ref, kind, terminals[0], terminals[1], value))
    names = {net.name for net in circuit.nets if not is_ground(net.name)}
    if elements and not any(e.node_a is None or e.node_b is None for e in elements):
        unsupported.extend(e.ref for e in elements)
    return ExtractedNetwork(elements, sorted(names), sorted(set(unsupported)), pin_nets)
