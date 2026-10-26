import math
from typing import Dict, List, Optional

import numpy as np

from server.features.repair_workbench.circuit_schemas import CircuitSpec
from server.features.repair_workbench.mna_elements import (
    Element,
    ExtractedNetwork,
    extract_network,
    is_ground,
)

def _stamp_admittance(matrix, index, element: Element, admittance: complex) -> None:
    a = index.get(element.node_a) if element.node_a else None
    b = index.get(element.node_b) if element.node_b else None
    if a is not None:
        matrix[a, a] += admittance
    if b is not None:
        matrix[b, b] += admittance
    if a is not None and b is not None:
        matrix[a, b] -= admittance
        matrix[b, a] -= admittance


def _solve_network(network: ExtractedNetwork, omega: float) -> Dict[str, complex]:
    index = {name: i for i, name in enumerate(network.nodes)}
    node_count = len(index)
    branches = [e for e in network.elements if e.kind == "V" or (e.kind == "L" and omega == 0.0)]
    size = node_count + len(branches)
    if size == 0 or network.unsupported:
        return {}
    matrix = np.zeros((size, size), dtype=complex)
    rhs = np.zeros(size, dtype=complex)
    for element in network.elements:
        if element.kind == "R":
            _stamp_admittance(matrix, index, element, 1.0 / element.value)
        elif element.kind == "C" and omega > 0.0:
            _stamp_admittance(matrix, index, element, 1j * omega * element.value)
        elif element.kind == "L" and omega > 0.0:
            _stamp_admittance(matrix, index, element, 1.0 / (1j * omega * element.value))
        elif element.kind == "I":
            a = index.get(element.node_a) if element.node_a else None
            b = index.get(element.node_b) if element.node_b else None
            if a is not None:
                rhs[a] -= element.value
            if b is not None:
                rhs[b] += element.value
    for offset, element in enumerate(branches):
        row = node_count + offset
        a = index.get(element.node_a) if element.node_a else None
        b = index.get(element.node_b) if element.node_b else None
        if a is not None:
            matrix[a, row] += 1.0
            matrix[row, a] += 1.0
        if b is not None:
            matrix[b, row] -= 1.0
            matrix[row, b] -= 1.0
        rhs[row] = element.value if element.kind == "V" else 0.0
    try:
        solution = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError:
        return {}
    if not np.all(np.isfinite(solution)) or not np.allclose(matrix @ solution, rhs):
        return {}
    return {name: complex(solution[i]) for name, i in index.items()}


def solve_dc(circuit: CircuitSpec) -> Dict[str, float]:
    network = extract_network(circuit)
    return {name: value.real for name, value in _solve_network(network, 0.0).items()}


def solve_ac(circuit: CircuitSpec, frequencies: List[float], output_net: str) -> List[Optional[float]]:
    network = extract_network(circuit)
    if output_net not in network.nodes or is_ground(output_net):
        return [None] * len(frequencies)
    gains: List[Optional[float]] = []
    for frequency in frequencies:
        if not math.isfinite(frequency) or frequency < 0:
            gains.append(None)
            continue
        voltage = _solve_network(network, 2.0 * math.pi * frequency).get(output_net, 0j)
        magnitude = abs(voltage)
        gains.append(20.0 * math.log10(magnitude) if magnitude > 1e-30 else None)
    return gains


def unsupported_refs(circuit: CircuitSpec) -> List[str]:
    return extract_network(circuit).unsupported
