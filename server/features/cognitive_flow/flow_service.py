from typing import List, Dict, Any, Optional
from server.core.telemetry.journey import journey, Journey

class CognitiveFlowService:
    @staticmethod
    def get_active_flow() -> Optional[Dict[str, Any]]:
        active = journey.active()
        if active:
            return active.snapshot()
        recent = journey.recent()
        if recent:
            return recent[0]
        return None

    @staticmethod
    def get_recent_flows(limit: int = 10) -> List[Dict[str, Any]]:
        items = journey.recent()
        return items[:limit]

    @staticmethod
    def create_mock_flow_if_empty() -> Dict[str, Any]:
        existing = journey.active() or (journey.recent()[0] if journey.recent() else None)
        if existing:
            return existing.snapshot() if isinstance(existing, Journey) else existing

        j = journey.begin("Progetto Ingegneria: Generazione CAD e Diagnostica Windows", "operatore_locale")
        with journey.span("laws", "Leggi Fondamentali", "Verifica Asimov & Zero-Trust") as h1:
            h1.ok("Nessuna violazione riscontrata")
        with journey.span("router", "System 1 Router", "Instradamento verso Swarm Agenti") as h3:
            h3.ok("Team assegnato: Chief, Windows Specialist, CAD Engineer")
        with journey.span("agent", "Windows System Agent", "Automazione ambiente e verifica processi", agent="windows_system_agent", tool="windows_powershell_exec", widget="windows_desktop_control_widget", parallel=True) as h4:
            h4.note("Esecuzione comando PowerShell: Get-Process | Validazione ambiente OS")
            h4.ok("Sessione Windows pronta")
        with journey.span("agent", "AutoCAD & 3D CAD Engineer", "Generazione disegno vettoriale DXF flangia", agent="autocad_designer", tool="cad_generate_dxf", widget="cad_viewport_viewer", parallel=True) as h5:
            h5.note("DXF R12 generato in data/cad_exports/flangia.dxf (Area: 140.2 cm2)")
            h5.ok("File DXF validato e pronto")
        with journey.span("supervisor", "Capo Agente (Chief)", "Supervisione 24/7 e calcolo avanzamento", agent="chief_supervisor", tool="chief_anti_loop_watchdog", widget="chief_supervision_hud") as h6:
            h6.note("Zero loop intercettati. Milestone avanzata al 45%. Proiezione widget completata.")
            h6.ok("Avanzamento convalidato")
        journey.finish("Flusso cognitivo eseguito: tutti gli agenti hanno risposto, tool eseguiti e widget proiettati a schermo.", "SUCCESS", "chief_supervisor")
        return j.snapshot()


cognitive_flow_service = CognitiveFlowService()
