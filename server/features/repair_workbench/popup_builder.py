from typing import Any, Dict, List

from server.features.repair_workbench.circuit_schemas import CircuitSpec
from server.features.repair_workbench.mna_elements import is_ground
from server.features.repair_workbench.session_models import (
    ARComponentPopup,
    ComponentHealth,
    DetectedComponent,
)


def voltages_for_ref(
    circuit: CircuitSpec, node_voltages: Dict[str, float], ref: str
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    if not node_voltages:
        return result
    for net in circuit.nets:
        for connection in net.connections:
            if connection.ref != ref:
                continue
            if is_ground(net.name):
                result[connection.pin] = 0.0
            elif net.name in node_voltages:
                result[connection.pin] = round(node_voltages[net.name], 4)
    return result


def build_popups(
    tracks: List[Dict[str, Any]],
    components_by_key: Dict[str, DetectedComponent],
    circuit: CircuitSpec,
    node_voltages: Dict[str, float],
    taught_keys: set,
) -> List[ARComponentPopup]:
    popups: List[ARComponentPopup] = []
    for track in tracks:
        label = str(track["label"])
        detected = components_by_key.get(label)
        ref = detected.ref if detected and detected.ref else None
        popups.append(
            ARComponentPopup(
                track_id=int(track["track_id"]),
                key=label,
                label=detected.label if detected else label,
                value=detected.value if detected else "",
                category=detected.category if detected else "other",
                bbox=[float(v) for v in track["bbox"]],
                health=detected.health if detected else ComponentHealth.UNKNOWN,
                notes=detected.notes if detected else "",
                expected_voltages=voltages_for_ref(circuit, node_voltages, ref) if ref else {},
                taught=label in taught_keys,
            )
        )
    return popups
