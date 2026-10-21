from typing import Dict, List

from server.features.repair_workbench.session_models import (
    BoardDossier,
    ComponentHealth,
    DetectedComponent,
    Message,
    VisionObservation,
)


def build_anomalies(
    netlist_issues: List[Dict[str, str]],
    unsupported: List[str],
    components: List[DetectedComponent],
) -> List[Message]:
    anomalies = [
        Message(
            key=f"workbench.anomaly.{issue['kind']}",
            params={"net": issue["net"], "detail": issue["detail"]},
        )
        for issue in netlist_issues
    ]
    for component in components:
        if component.health in (ComponentHealth.SUSPECT, ComponentHealth.FAULT):
            anomalies.append(
                Message(
                    key=f"workbench.anomaly.component_{component.health.value}",
                    params={"ref": component.key, "note": component.notes},
                )
            )
    if unsupported:
        anomalies.append(
            Message(
                key="workbench.anomaly.simulation_skipped",
                params={"refs": ", ".join(unsupported[:12])},
            )
        )
    return anomalies


def build_advice(
    anomalies: List[Message], observation: VisionObservation
) -> List[Message]:
    advice = [Message(text=text) for text in observation.advice if text]
    for anomaly in anomalies:
        if anomaly.key in (
            "workbench.anomaly.component_fault",
            "workbench.anomaly.component_suspect",
        ):
            advice.append(
                Message(key="workbench.advice.inspect_component", params=anomaly.params)
            )
        elif anomaly.key == "workbench.anomaly.missing_ground":
            advice.append(Message(key="workbench.advice.verify_ground"))
    return advice[:12]


def build_dossier(
    observation: VisionObservation,
    component_count: int,
    anomalies: List[Message],
) -> BoardDossier:
    return BoardDossier(
        title=observation.title,
        board_kind=observation.board_kind,
        summary=observation.summary,
        characteristics=observation.characteristics,
        anomalies=anomalies,
        component_count=component_count,
    )
