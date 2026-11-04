from typing import List

from server.features.repair_workbench.session_models import WorkbenchSession

MAX_COMPONENTS_IN_CONTEXT = 40


def build_session_context(session: WorkbenchSession) -> str:
    components: List[str] = [
        f"{c.ref}={c.value or '?'}({c.category.value})"
        for c in session.circuit.components[:MAX_COMPONENTS_IN_CONTEXT]
    ]
    anomalies = [a.key or a.text or "" for a in session.dossier.anomalies]
    voltages = [f"{name}={value}V" for name, value in list(session.expected_voltages.items())[:20]]
    parts = [
        f"Board: {session.dossier.title} / {session.dossier.board_kind}",
        f"Summary: {session.dossier.summary}",
        f"Components: {', '.join(components) or 'none identified'}",
        f"Anomalies: {', '.join(anomalies) or 'none'}",
        f"Simulated DC node voltages: {', '.join(voltages) or 'not available'}",
    ]
    return "\n".join(parts)
