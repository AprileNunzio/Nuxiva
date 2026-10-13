import re
import time
from dataclasses import dataclass, field
from typing import Any

from features.team.board import board
from state import store


@dataclass
class SpecialistRole:
    role_id: str
    name: str
    description: str
    keywords: list[str]
    domains: list[str]
    preferred_tools: list[str] = field(default_factory=list)


SPECIALIST_ROSTER: dict[str, SpecialistRole] = {
    "sysadmin": SpecialistRole(
        role_id="sysadmin",
        name="Ingegnere di Sistema & DevOps",
        description="Gestione del server, aggiornamenti via GitHub o SSH, servizi systemd, Docker, memoria, disco, processi e diagnostica.",
        keywords=["aggiorna", "upgrade", "github", "ssh", "bloccato", "riavvia", "servizio", "systemctl", "docker", "disco", "cpu", "memoria", "kernel", "pacchetto", "installazione", "sfondo", "background"],
        domains=["actions", "auto_update", "governor", "selftest", "proxmox"],
        preferred_tools=["run_command", "system_status", "service_restart", "package_install"]
    ),
    "coder": SpecialistRole(
        role_id="coder",
        name="Architetto Software & Sviluppatore",
        description="Progettazione ed esecuzione di codice sorgente, debug, script, algoritmi, calcoli matematici e refactoring.",
        keywords=["codice", "script", "programma", "python", "bash", "funzione", "classe", "bug", "errore", "calcola", "formula", "algoritmo", "sviluppa"],
        domains=["code", "forge", "selftest"],
        preferred_tools=["write_file", "run_script", "eval_math"]
    ),
    "domotica": SpecialistRole(
        role_id="domotica",
        name="Specialista Smart Home & IoT",
        description="Controllo integrato di dispositivi smart, luci, climatizzazione, prese e automazioni tramite Home Assistant.",
        keywords=["luce", "luci", "accendi", "spegni", "temperatura", "termostato", "casa", "stanza", "salotto", "camera", "sensore", "interruttore", "tapparella"],
        domains=["home", "home_assistant", "scene"],
        preferred_tools=["home_control", "home_state"]
    ),
    "vision": SpecialistRole(
        role_id="vision",
        name="Specialista Computer Vision & Multimodale",
        description="Analisi visiva, telecamere di sicurezza, flussi video, riconoscimento volti, persone ed elementi nell'ambiente.",
        keywords=["guarda", "telecamera", "webcam", "video", "vedi", "fotocamera", "chi c'è", "chi vedi", "riconosci", "inquadra"],
        domains=["vision", "cameras", "livecam"],
        preferred_tools=["camera_snapshot", "vision_inspect"]
    ),
    "audio": SpecialistRole(
        role_id="audio",
        name="Specialista Elaborazione Audio & Voce",
        description="Elaborazione del segnale vocale, microfoni, cancellazione rumore, sintesi vocale e gestione riproduzione musicale.",
        keywords=["musica", "canzone", "volume", "audio", "microfono", "voce", "suona", "ascolta", "silenzio", "rumore", "spotify"],
        domains=["audio", "ear", "sounds", "music", "spotify", "voicestudio"],
        preferred_tools=["play_music", "sound_control", "set_volume"]
    ),
    "secretary": SpecialistRole(
        role_id="secretary",
        name="Segretario Esecutivo & Comunicazioni",
        description="Gestione delle comunicazioni verso l'esterno, messaggi Telegram, email, agenda, promemoria e contatti personali.",
        keywords=["telegram", "messaggio", "invia", "scrivi a", "email", "posta", "promemoria", "ricordami", "agenda", "calendario", "contatto"],
        domains=["telegram", "automations", "people"],
        preferred_tools=["send_telegram", "send_email", "add_reminder"]
    ),
    "research": SpecialistRole(
        role_id="research",
        name="Specialista Ricerca & Gestione Dati",
        description="Ricerca documentale, consultazione file condivisi, recupero informazioni e archiviazione dati strutturati.",
        keywords=["cerca documento", "file", "trova pdf", "archivio", "cartella", "documento", "leggi file", "condivisione"],
        domains=["documents", "shares", "vault"],
        preferred_tools=["find_files", "read_document"]
    ),
    "security": SpecialistRole(
        role_id="security",
        name="Auditor di Sicurezza & Conformità",
        description="Verifica policy di sicurezza, protezione credenziali, vault, chiavi API, firewall, VPN e tutela della privacy.",
        keywords=["sicurezza", "password", "chiave", "token", "permesso", "autorizzazione", "firewall", "vpn", "privacy", "segreto"],
        domains=["vault", "authz", "firewall", "vpn", "laws"],
        preferred_tools=["vault_read", "check_permission"]
    ),
    "advisor": SpecialistRole(
        role_id="advisor",
        name="Consulente Strategico & Dialogo Generale",
        description="Ragionamento generale, comprensione contestuale profonda, consulenza strategica e sintesi cognitiva.",
        keywords=["perché", "spiegami", "cosa ne pensi", "opinione", "aiuto", "come funziona", "consigliami", "chi sei"],
        domains=["brain", "chat", "understanding"],
        preferred_tools=["brain_reason"]
    )
}


@dataclass
class CEODecision:
    primary_role: SpecialistRole
    secondary_roles: list[SpecialistRole]
    delegation_plan: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


class CEOExecutive:
    """
    CEO Orchestrator di Nuxiva:
    Ogni conversazione viene diretta e supervisionata dal CEO, che agisce come vertice
    esecutivo dell'architettura multi-agente. Il CEO analizza l'intento dell'utente,
    scompone gli obiettivi complessi, delega l'esecuzione allo specialista di dominio
    più qualificato, monitora l'avanzamento sulla lavagna di squadra e consolida
    la risposta finale garantendo coerenza, sicurezza e standard elevati.
    """

    def __init__(self) -> None:
        self.active_briefings: dict[str, CEODecision] = {}

    def analyze_request(self, text: str, context: dict | None = None) -> CEODecision:
        query = (text or "").strip().lower()
        scores: dict[str, float] = {}

        for role_id, role in SPECIALIST_ROSTER.items():
            score = 0.0
            for kw in role.keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", query, re.IGNORECASE):
                    score += 2.0
                elif kw in query:
                    score += 1.0
            scores[role_id] = score

        sorted_roles = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_role_id, top_score = sorted_roles[0]

        if top_score < 1.0:
            top_role_id = "advisor"

        primary = SPECIALIST_ROSTER[top_role_id]
        secondaries = [SPECIALIST_ROSTER[rid] for rid, sc in sorted_roles[1:3] if sc > 0]

        plan = f"Il CEO assegna l'incarico primario a «{primary.name}» per il dominio {primary.role_id}."
        if secondaries:
            plan += f" Coinvolti come supporto: {', '.join(s.name for s in secondaries)}."

        return CEODecision(
            primary_role=primary,
            secondary_roles=secondaries,
            delegation_plan=plan,
            confidence=min(1.0, 0.5 + (top_score * 0.1))
        )

    def on_conversation_start(self, text: str, context: dict | None = None) -> CEODecision:
        decision = self.analyze_request(text, context)
        store.event("INFO", f"CEO ha preso in carico la richiesta: {decision.delegation_plan}", "ceo")
        board.post("ceo", decision.primary_role.role_id, f"Incarico: {text[:120]} (strategia: {decision.delegation_plan})", "direttiva")
        return decision

    def synthesize(self, decision: CEODecision, raw_result: dict) -> dict:
        result = dict(raw_result)
        specialist_title = decision.primary_role.name

        result["ceo"] = {
            "orchestrator": "CEO Executive",
            "delegated_to": decision.primary_role.role_id,
            "specialist": specialist_title,
            "plan": decision.delegation_plan,
            "confidence": decision.confidence
        }

        # Mostra chiaramente la leadership del CEO e lo specialista intervenuto
        current_agent = result.get("agent")
        if not current_agent or current_agent in ("core", "nuxiva_ui", "assistente"):
            result["agent"] = f"CEO → {specialist_title}"
        elif not current_agent.startswith("CEO"):
            result["agent"] = f"CEO [{specialist_title}] · {current_agent}"

        board.post("ceo", "tutti", f"Incarico completato con successo da {specialist_title}", "conferma")
        return result

    def get_team_overview(self) -> dict[str, Any]:
        return {
            "ceo": "Chief Executive Orchestrator",
            "mission": "Gestione strategica unificata e delega coordinata della squadra di agenti specializzati",
            "specialists": [
                {
                    "id": role.role_id,
                    "name": role.name,
                    "description": role.description,
                    "domains": role.domains,
                    "preferred_tools": role.preferred_tools
                }
                for role in SPECIALIST_ROSTER.values()
            ]
        }


ceo = CEOExecutive()
