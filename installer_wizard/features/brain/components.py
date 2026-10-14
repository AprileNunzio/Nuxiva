import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Component:
    id: str
    label: str
    group: str
    role: str
    hint: str
    side: str = "supervisor"


COMPONENTS: tuple[Component, ...] = (
    Component("conversation", "Conversazione", "Dialogo", "chat", "Risposte parlate e chat; il sistema sceglie tra veloce e ragionamento."),
    Component("agent", "Agente di sistema", "Dialogo", "deep", "Sceglie ed esegue gli strumenti del sistema operativo."),
    Component("mind", "Memoria e ricordi", "Dialogo", "chat", "Estrae e ordina ciò che Nuxiva ricorda di te."),
    Component("presentation", "Impaginazione dei contenuti", "Dialogo", "chat", "Sceglie come mostrare le risposte: testo, passi, tabelle, immagini, modelli 3D."),
    Component("diary", "Diario", "Dialogo", "chat", "Riassunti della giornata."),
    Component("actions", "Azioni rapide", "Dialogo", "chat", "Calcoli e comandi brevi."),
    Component("home_commands", "Comandi domotici", "Casa", "domotico", "Interpreta i comandi per luci, scene e dispositivi."),
    Component("automations", "Automazioni", "Casa", "deep", "Trasforma una frase in una regola automatica."),
    Component("documents", "Documenti", "Servizi", "deep", "Piani e stesura di documenti."),
    Component("firewall", "Analista di sicurezza di rete", "Servizi", "deep", "Valuta gli allarmi del firewall e propone contromisure."),
    Component("skills", "Abilità", "Servizi", "studio", "Generazione di nuove abilità."),
    Component("study", "Studio autonomo", "Servizi", "studio", "Lettura di fonti, esercizi ed esami a riposo."),
    Component("models3d", "Editor modelli 3D", "Servizi", "modello3d", "Disegno di oggetti nell'editor."),
    Component("research", "Ricercatore", "Agenti del Core", "ricercatore", "Ricerche sul web e sintesi di fonti.", "core"),
    Component("domotics", "Domotico", "Agenti del Core", "domotico", "Esecuzione di scene e comandi per la casa.", "core"),
    Component("skill_synthesizer", "Sintetizzatore di strumenti", "Agenti del Core", "studio", "Scrive strumenti dinamici in sandbox.", "core"),
    Component("tool_builder", "Costruttore di strumenti", "Agenti del Core", "studio", "Costruisce strumenti nei piani a grafo.", "core"),
    Component("genera_modello_3d", "Generatore 3D", "Agenti del Core", "modello3d", "Strumento di generazione 3D.", "core"),
    Component("parametric_designer", "Progettista parametrico", "Agenti del Core", "modello3d", "Da richiesta a specifica e file CAD.", "core"),
    Component("agent_self_healing_coder", "Architetto web (coder)", "Agenti del Core", "coder", "Scrive siti e app e li ripara da solo.", "core"),
    Component("analytic_reasoner", "Ragionatore analitico", "Agenti del Core", "deep", "Analisi e ragionamento puro.", "core"),
    Component("home_assistant_agent", "Agente Home Assistant", "Agenti del Core", "domotico", "Controlla i dispositivi tramite Home Assistant.", "core"),
    Component("sysops_agent", "Agente di sistema (Core)", "Agenti del Core", "coder", "Automazione e manutenzione del sistema.", "core"),
    Component("surveillance_agent", "Agente di sorveglianza", "Agenti del Core", "deep", "Interpreta eventi e immagini delle telecamere.", "core"),
    Component("intent_classifier", "Classificatore di intenti", "Cervello cognitivo", "chat", "Capisce cosa vuoi fare prima di instradare.", "core"),
    Component("kernel_planner", "Pianificatore a grafo", "Cervello cognitivo", "deep", "Scompone i compiti complessi in un DAG.", "core"),
    Component("kernel_critic", "Critico finale", "Cervello cognitivo", "deep", "Giudica il risultato prima di consegnarlo.", "core"),
    Component("consensus_security", "Consenso: sicurezza", "Cervello cognitivo", "deep", "Voto con veto sulle operazioni distruttive.", "core"),
    Component("consensus_proportionality", "Consenso: proporzionalità", "Cervello cognitivo", "deep", "Voto sulla necessità dei passi.", "core"),
    Component("consensus_reversibility", "Consenso: reversibilità", "Cervello cognitivo", "deep", "Voto sulla recuperabilità degli errori.", "core"),
)

BY_ID: dict[str, Component] = {c.id: c for c in COMPONENTS}


@dataclass
class SynapticSpike:
    source_neuron: str
    target_cluster: str
    potential: float
    inhibitory_gaba: bool = False
    emotion_vector: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    payload: Any = None
    timestamp: float = field(default_factory=time.time)


class SpikingNeuronNode:
    def __init__(
        self,
        node_id: str,
        threshold: float = 0.85,
        tau_m: float = 0.05,
        rest_potential: float = 0.0,
        reset_potential: float = -0.1,
        refractory_period_s: float = 0.005,
    ) -> None:
        self.node_id = node_id
        self.threshold = threshold
        self.tau_m = max(0.001, tau_m)
        self.rest_potential = rest_potential
        self.reset_potential = reset_potential
        self.refractory_period_s = refractory_period_s
        self.potential = rest_potential
        self.last_spike_ts = 0.0
        self.last_update_ts = time.time()
        self.synaptic_weights: dict[str, float] = {}

    def set_weight(self, source_id: str, weight: float) -> None:
        self.synaptic_weights[source_id] = max(0.0, min(1.0, weight))

    def get_weight(self, source_id: str) -> float:
        return self.synaptic_weights.get(source_id, 0.5)

    def compute_decay(self, now: float) -> float:
        dt = max(0.0, now - self.last_update_ts)
        self.last_update_ts = now
        return math.exp(-dt / self.tau_m)

    async def integrate_and_fire(self, trigger: SynapticSpike, limbic: Any) -> list[SynapticSpike]:
        now = time.time()
        if (now - self.last_spike_ts) < self.refractory_period_s:
            return []

        decay = self.compute_decay(now)
        self.potential = self.rest_potential + (self.potential - self.rest_potential) * decay

        w_ij = self.get_weight(trigger.source_neuron)
        s_j = -1.0 if trigger.inhibitory_gaba else 1.0

        dopamine = getattr(limbic, "dopamine", 0.5)
        cortisol = getattr(limbic, "cortisol", 0.1)
        m_limbic = 1.0 + 0.3 * dopamine - 0.2 * cortisol

        delta_v = w_ij * s_j * trigger.potential * max(0.1, m_limbic)
        self.potential = max(-1.0, min(2.0, self.potential + delta_v))

        modulate_fn = getattr(limbic, "modulate_firing_threshold", None)
        effective_threshold = modulate_fn(self.threshold) if callable(modulate_fn) else self.threshold

        if self.potential >= effective_threshold:
            fired_potential = self.potential
            self.potential = self.reset_potential
            self.last_spike_ts = now
            vector = getattr(limbic, "to_vector", lambda: [0.0, 0.0, 0.0, 0.0])()
            return [
                SynapticSpike(
                    source_neuron=self.node_id,
                    target_cluster=trigger.target_cluster,
                    potential=fired_potential,
                    inhibitory_gaba=False,
                    emotion_vector=vector,
                    payload=trigger.payload,
                    timestamp=now,
                )
            ]

        return []
