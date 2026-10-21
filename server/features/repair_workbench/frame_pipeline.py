from typing import Dict, List, Set

from server.features.repair_workbench.diagnostics import (
    build_advice,
    build_anomalies,
    build_dossier,
)
from server.features.repair_workbench.mna_solver import solve_dc, unsupported_refs
from server.features.repair_workbench.native_bridge import WorkbenchEngine
from server.features.repair_workbench.popup_builder import build_popups
from server.features.repair_workbench.schematic_synthesizer import merge_observation
from server.features.repair_workbench.session_models import (
    DetectedComponent,
    VisionObservation,
    WorkbenchSession,
)


def _netlist_payload(session: WorkbenchSession) -> List[Dict[str, object]]:
    return [
        {
            "name": net.name,
            "pins": [{"reference": c.ref, "pin": c.pin} for c in net.connections],
        }
        for net in session.circuit.nets
    ]


def _resolve_components(
    session: WorkbenchSession, observation: VisionObservation
) -> tuple:
    resolved: List[DetectedComponent] = []
    taught_refs: Set[str] = set()
    for component in observation.components:
        label = session.aliases.get(component.key)
        if label is None:
            resolved.append(component)
            continue
        update = {"label": label}
        if label in session.taught_values:
            update["value"] = session.taught_values[label]
        resolved.append(component.model_copy(update=update))
        if component.ref:
            taught_refs.add(component.ref)
    return resolved, taught_refs


def _label_of(session: WorkbenchSession, component: DetectedComponent) -> str:
    return session.aliases.get(component.key, component.key)


def apply_observation(
    session: WorkbenchSession, engine: WorkbenchEngine, observation: VisionObservation
) -> None:
    session.vision_model = observation.model_used
    components, taught_refs = _resolve_components(session, observation)
    detections = [
        {"label": _label_of(session, original), "bbox": resolved.bbox, "score": resolved.score}
        for original, resolved in zip(observation.components, components)
    ]
    tracks = engine.update_tracks(detections)
    merge_observation(session.circuit, observation, components, taught_refs)
    by_label = {
        _label_of(session, original): resolved
        for original, resolved in zip(observation.components, components)
    }
    node_voltages = solve_dc(session.circuit)
    session.expected_voltages = {k: round(v, 4) for k, v in node_voltages.items()}
    session.popups = build_popups(
        tracks, by_label, session.circuit, node_voltages, set(session.aliases.values())
    )
    issues = engine.validate_netlist(_netlist_payload(session))
    anomalies = build_anomalies(issues, unsupported_refs(session.circuit), components)
    session.dossier = build_dossier(observation, len(session.circuit.components), anomalies)
    session.advice = build_advice(anomalies, observation)
