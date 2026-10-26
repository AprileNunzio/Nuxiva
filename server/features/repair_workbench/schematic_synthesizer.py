from typing import List, Set

from server.features.repair_workbench.circuit_schemas import (
    CircuitSpec,
    ComponentCategory,
    ComponentSpec,
    NetSpec,
    PinRef,
)
from server.features.repair_workbench.session_models import (
    DetectedComponent,
    VisionObservation,
)


def _upsert_component(
    circuit: CircuitSpec, detected: DetectedComponent, taught_refs: Set[str]
) -> None:
    ref = detected.ref
    if ref is None:
        return
    taught = ref in taught_refs
    existing = circuit.get_component(ref)
    if existing is None:
        circuit.components.append(
            ComponentSpec(
                ref=ref,
                value=detected.value,
                category=detected.category,
                description=detected.label,
            )
        )
        return
    if detected.value and (not existing.value or taught):
        existing.value = detected.value
    if taught:
        existing.description = detected.label
    if existing.category == ComponentCategory.OTHER:
        existing.category = detected.category
    if not existing.description:
        existing.description = detected.label


def _ensure_component(circuit: CircuitSpec, ref: str) -> None:
    if circuit.get_component(ref) is None:
        circuit.components.append(ComponentSpec(ref=ref))


def _merge_connections(circuit: CircuitSpec, observation: VisionObservation) -> None:
    for hint in observation.connections:
        net = circuit.get_net(hint.net)
        if net is None:
            net = NetSpec(name=hint.net)
            circuit.nets.append(net)
        known = {(c.ref, c.pin) for c in net.connections}
        for pin in hint.pins:
            if (pin.ref, pin.pin) in known:
                continue
            _ensure_component(circuit, pin.ref)
            net.connections.append(PinRef(ref=pin.ref, pin=pin.pin))
            known.add((pin.ref, pin.pin))


def merge_observation(
    circuit: CircuitSpec,
    observation: VisionObservation,
    components: List[DetectedComponent],
    taught_refs: Set[str],
) -> None:
    for detected in components:
        _upsert_component(circuit, detected, taught_refs)
    _merge_connections(circuit, observation)
    if observation.title and not circuit.name:
        circuit.name = observation.title
    if observation.summary and not circuit.description:
        circuit.description = observation.summary[:240]
