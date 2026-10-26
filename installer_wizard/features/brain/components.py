import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


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
    Component("projects", "Progetti", "Servizi", "deep", "Pianificazione e avanzamento dei progetti di lavoro."),
    Component("firewall", "Analista di sicurezza di rete", "Servizi", "deep", "Valuta gli allarmi del firewall e propone contromisure."),
    Component("skills", "Abilità", "Servizi", "studio", "Generazione di nuove abilità."),
    Component("study", "Studio autonomo", "Servizi", "studio", "Lettura di fonti, esercizi ed esami a riposo."),
    Component("ceo", "CEO Orchestrator", "Dialogo", "chat", "Ragiona sulle richieste ambigue e sceglie lo specialista giusto."),
    Component("diorama", "Creatore di diorami", "Servizi", "deep", "Compone diorami fotorealistici dal vivo, a strati."),
    Component("musicstudio", "Studio musicale", "Servizi", "deep", "Pianifica canzoni, scrive testi e li traduce nello studio musicale."),
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

AGENT_PREFIX = "agent:"
AGENT_REF = re.compile(r"^agent:[a-z0-9][a-z0-9_-]{0,63}$")


class ComponentIndex(dict):

    def __contains__(self, key) -> bool:
        return dict.__contains__(self, key) or (isinstance(key, str) and AGENT_REF.fullmatch(key) is not None)

    def __missing__(self, key) -> Component:
        if isinstance(key, str) and AGENT_REF.fullmatch(key):
            return Component(key, key[len(AGENT_PREFIX):], "Agenti", "deep", "Modello scelto per questo agente.", "agents")
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


BY_ID: dict[str, Component] = ComponentIndex((c.id, c) for c in COMPONENTS)


def agent_component(agent_id: str) -> str:
    if agent_id in COMPONENTS_STATIC:
        return agent_id
    return f"{AGENT_PREFIX}{re.sub(r'[^a-z0-9_-]', '-', str(agent_id).lower()).strip('-')[:64] or 'agent'}"


COMPONENTS_STATIC = frozenset(c.id for c in COMPONENTS)


@dataclass
class LimbicModulator:
    valence: float = 0.0
    arousal: float = 0.4
    dominance: float = 0.5
    dopamine: float = 0.5
    noradrenaline: float = 0.2
    serotonin: float = 0.7
    cortisol: float = 0.1

    def ingest_biometrics(
        self,
        vocal_stress: float = 0.0,
        facial_valence: float = 0.0,
        heart_rate_delta: float = 0.0,
        system_pressure: float = 0.0,
    ) -> None:
        self.valence = max(-1.0, min(1.0, (self.valence * 0.6) + (facial_valence * 0.4)))
        self.arousal = max(0.0, min(1.0, (self.arousal * 0.5) + (vocal_stress * 0.3) + (heart_rate_delta * 0.2)))
        self.noradrenaline = max(0.05, min(1.0, (self.arousal * 0.7) + (vocal_stress * 0.3)))
        self.cortisol = max(0.05, min(1.0, (system_pressure * 0.5) + (max(0.0, -self.valence) * 0.5)))
        self.dopamine = max(0.05, min(1.0, 0.5 + (self.valence * 0.4) - (self.cortisol * 0.2)))
        self.serotonin = max(0.05, min(1.0, 1.0 - (self.noradrenaline * 0.5) - (self.cortisol * 0.3)))

    def compute_threshold(self, base_threshold: float) -> float:
        urgency_multiplier = 1.0 - (self.noradrenaline * 0.45)
        cortisol_gate = self.cortisol * 0.15
        return max(0.12, (base_threshold * urgency_multiplier) + cortisol_gate)

    def modulate_firing_threshold(self, base_threshold: float) -> float:
        return self.compute_threshold(base_threshold)

    def parallel_branch_budget(self, max_branches: int) -> int:
        if self.cortisol > 0.8:
            return max(1, max_branches // 4)
        exploration_boost = 0.5 + (self.dopamine * 0.5) + (self.serotonin * 0.2)
        return max(1, min(max_branches, int(round(max_branches * exploration_boost))))

    def to_vector(self) -> List[float]:
        return [self.valence, self.arousal, self.dopamine, self.noradrenaline]


@dataclass(order=True)
class SynapticSpike:
    sort_index: float = field(init=False, repr=False)
    source_id: str = field(compare=False)
    target_id: str = field(compare=False)
    potential: float = field(compare=False)
    inhibitory: bool = field(default=False, compare=False)
    payload: Dict[str, Any] = field(default_factory=dict, compare=False)
    timestamp: float = field(default_factory=time.perf_counter, compare=False)
    emotion_vector: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0], compare=False)

    def __init__(
        self,
        source_id: str = "",
        target_id: str = "",
        potential: float = 0.0,
        inhibitory: bool = False,
        payload: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
        emotion_vector: Optional[List[float]] = None,
        source_neuron: Optional[str] = None,
        target_cluster: Optional[str] = None,
        inhibitory_gaba: Optional[bool] = None,
    ) -> None:
        self.source_id = source_neuron if source_neuron is not None else source_id
        self.target_id = target_cluster if target_cluster is not None else target_id
        self.potential = potential
        self.inhibitory = inhibitory_gaba if inhibitory_gaba is not None else inhibitory
        self.payload = payload if payload is not None else {}
        self.timestamp = timestamp if timestamp is not None else time.perf_counter()
        self.emotion_vector = emotion_vector if emotion_vector is not None else [0.0, 0.0, 0.0, 0.0]
        self.sort_index = -self.potential

    @property
    def source_neuron(self) -> str:
        return self.source_id

    @property
    def target_cluster(self) -> str:
        return self.target_id

    @property
    def inhibitory_gaba(self) -> bool:
        return self.inhibitory


class SpikingNeuron:
    def __init__(
        self,
        neuron_id: str,
        role: str = "cortex",
        base_threshold: float = 0.65,
        tau_m: float = 0.08,
        resistance: float = 1.2,
        kernel: Optional[Callable[[Dict[str, Any], LimbicModulator], Awaitable[Dict[str, Any]]]] = None,
    ) -> None:
        self.neuron_id = neuron_id
        self.role = role
        self.base_threshold = base_threshold
        self.tau_m = max(0.001, tau_m)
        self.resistance = resistance
        self.kernel = kernel
        self.potential: float = 0.0
        self.resting_potential: float = 0.0
        self.last_spike_in: float = time.perf_counter()
        self.last_fired_at: float = 0.0
        self.refractory_until: float = 0.0
        self.synapses: Dict[str, float] = {}
        self.trace_history: Dict[str, float] = {}

    def connect(self, target_id: str, weight: float = 0.6) -> None:
        self.synapses[target_id] = max(0.01, min(2.5, weight))

    def integrate(self, spike: SynapticSpike) -> float:
        now = time.perf_counter()
        if now < self.refractory_until:
            return self.potential
        dt = max(1e-6, now - self.last_spike_in)
        decay = math.exp(-dt / self.tau_m)
        self.potential = self.resting_potential + (self.potential - self.resting_potential) * decay
        self.last_spike_in = now
        self.trace_history[spike.source_id] = now
        weight = self.synapses.get(spike.source_id, 1.0)
        if spike.inhibitory:
            self.potential = max(0.0, self.potential - (spike.potential * weight * self.resistance * 1.5))
        else:
            self.potential += spike.potential * weight * self.resistance
        return self.potential

    async def evaluate_and_fire(
        self,
        context_payload: Dict[str, Any],
        limbic: LimbicModulator,
    ) -> List[SynapticSpike]:
        now = time.perf_counter()
        if now < self.refractory_until:
            return []
        active_threshold = limbic.compute_threshold(self.base_threshold)
        if self.potential < active_threshold:
            return []
        firing_strength = self.potential
        self.potential = self.resting_potential
        self.last_fired_at = now
        self.refractory_until = now + max(0.005, 0.04 * (1.0 - limbic.noradrenaline * 0.6))
        if self.kernel is not None:
            output = await self.kernel(context_payload, limbic)
        else:
            output = dict(context_payload)
        confidence = float(output.get("confidence", min(1.0, firing_strength)))
        inhibit_others = bool(output.get("inhibit_competitors", confidence >= 0.88))
        emitted: List[SynapticSpike] = []
        for target_id, weight in self.synapses.items():
            out_potential = confidence * weight * (1.0 + (limbic.dopamine * 0.25))
            emitted.append(
                SynapticSpike(
                    source_id=self.neuron_id,
                    target_id=target_id,
                    potential=out_potential,
                    inhibitory=inhibit_others and target_id.startswith("inhib_"),
                    payload={
                        **output,
                        "neuron_id": self.neuron_id,
                        "role": self.role,
                        "confidence": confidence,
                    },
                    emotion_vector=limbic.to_vector(),
                )
            )
        return emitted

    def apply_stdp(
        self,
        post_neuron_id: str,
        post_fired_at: float,
        reward_signal: float = 1.0,
        a_plus: float = 0.06,
        a_minus: float = 0.04,
        tau_stdp: float = 0.05,
    ) -> float:
        if post_neuron_id not in self.synapses or self.last_fired_at <= 0.0:
            return self.synapses.get(post_neuron_id, 0.0)
        dt = post_fired_at - self.last_fired_at
        if dt > 0:
            delta_w = a_plus * math.exp(-dt / tau_stdp) * reward_signal
        else:
            delta_w = -a_minus * math.exp(dt / tau_stdp)
        updated = max(0.01, min(2.5, self.synapses[post_neuron_id] + delta_w))
        self.synapses[post_neuron_id] = updated
        return updated


class SpikingNeuronNode(SpikingNeuron):
    def __init__(
        self,
        node_id: str,
        threshold: float = 0.85,
        tau_m: float = 0.05,
        rest_potential: float = 0.0,
        reset_potential: float = -0.1,
        refractory_period_s: float = 0.005,
    ) -> None:
        super().__init__(neuron_id=node_id, role="cortex", base_threshold=threshold, tau_m=tau_m)
        self.node_id = node_id
        self.threshold = threshold
        self.rest_potential = rest_potential
        self.reset_potential = reset_potential
        self.refractory_period_s = refractory_period_s

    def set_weight(self, source_id: str, weight: float) -> None:
        self.connect(source_id, weight)

    def get_weight(self, source_id: str) -> float:
        return self.synapses.get(source_id, 0.5)

    async def integrate_and_fire(self, trigger: SynapticSpike, limbic: Any = None) -> List[SynapticSpike]:
        now = time.time()
        if (now - self.last_fired_at) < self.refractory_period_s:
            return []
        lim = limbic if isinstance(limbic, LimbicModulator) else LimbicModulator()
        self.integrate(trigger)
        effective_thresh = lim.compute_threshold(self.threshold)
        if self.potential >= effective_thresh:
            fired_p = self.potential
            self.potential = self.reset_potential
            self.last_fired_at = now
            return [
                SynapticSpike(
                    source_id=self.node_id,
                    target_id=trigger.target_cluster,
                    potential=fired_p,
                    inhibitory=False,
                    payload=trigger.payload,
                    timestamp=now,
                    emotion_vector=lim.to_vector(),
                )
            ]
        return []
