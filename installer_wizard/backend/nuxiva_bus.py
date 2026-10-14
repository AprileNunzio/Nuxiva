import asyncio
import collections
import inspect
import json
import logging
import math
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from bus_router import ENGINE, matches, new_router, valid_origin, valid_pattern, valid_topic

log = logging.getLogger("nuxiva.bus")

SCHEMA_VERSION = "1.0"
MAX_PAYLOAD = 64 * 1024
MAX_RETAINED = 2048
DISCOVERY_TTL = 90.0
DEFAULT_RING_SIZE = 1024


class BusError(ValueError):
    pass


@dataclass(frozen=True)
class Envelope:
    id: str
    topic: str
    ts: float
    origin: str
    schema: str
    payload: dict = field(default_factory=dict)
    retain: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SynapticSpike:
    source_neuron: str
    target_cluster: str
    potential: float
    inhibitory_gaba: bool = False
    emotion_vector: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    payload: Any = None
    timestamp: float = field(default_factory=time.time)


class SynapticWeightMatrix:
    def __init__(self, default_weight: float = 0.5) -> None:
        self.default_weight = default_weight
        self._weights: dict[tuple[str, str], float] = {}
        self.a_plus = 0.015
        self.a_minus = 0.012
        self.tau_plus = 20.0
        self.tau_minus = 20.0

    def get(self, pre: str, post: str) -> float:
        return self._weights.get((pre, post), self.default_weight)

    def set(self, pre: str, post: str, weight: float) -> None:
        self._weights[(pre, post)] = max(0.0, min(1.0, weight))

    def apply_stdp(self, pre: str, post: str, delta_t_ms: float, dopamine: float = 0.5, is_reward: bool = True) -> float:
        current = self.get(pre, post)
        if delta_t_ms > 0.0 and is_reward:
            exp_term = math.exp(-delta_t_ms / max(0.1, self.tau_plus))
            delta_w = self.a_plus * exp_term * (1.0 + max(0.0, min(1.0, dopamine)))
        else:
            exp_term = math.exp(delta_t_ms / max(0.1, self.tau_minus))
            delta_w = -self.a_minus * exp_term
        updated = max(0.0, min(1.0, current + delta_w))
        self.set(pre, post, updated)
        return updated


class Subscription:
    def __init__(self, bus: "NuxivaBus", sid: int, pattern: str, callback: Callable[[Envelope], Any]) -> None:
        self.bus, self.sid, self.pattern, self.callback = bus, sid, pattern, callback

    def cancel(self) -> None:
        self.bus._remove(self)


class NuxivaBus:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._router = new_router()
        self._subs: dict[int, Subscription] = {}
        self._retained: dict[str, Envelope] = {}
        self._modules: dict[str, dict] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self.published = 0
        self.failures = 0
        self._spike_ring: collections.deque[SynapticSpike] = collections.deque(maxlen=DEFAULT_RING_SIZE)
        self.synaptic_weights = SynapticWeightMatrix()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, pattern: str, callback: Callable[[Envelope], Any], replay: bool = False) -> Subscription:
        if not valid_pattern(pattern):
            raise BusError(f"invalid topic pattern: {pattern!r}")
        with self._lock:
            try:
                sid = self._router.subscribe(pattern)
            except RuntimeError as exc:
                raise BusError(str(exc)) from exc
            sub = Subscription(self, sid, pattern, callback)
            self._subs[sid] = sub
            backlog = [e for t, e in sorted(self._retained.items()) if matches(pattern, t)] if replay else []
        for envelope in backlog:
            self._deliver(sub, envelope)
        return sub

    def _remove(self, sub: Subscription) -> None:
        with self._lock:
            if self._subs.get(sub.sid) is sub:
                del self._subs[sub.sid]
                self._router.unsubscribe(sub.sid)

    def publish_spike(
        self,
        source_neuron: str,
        target_cluster: str,
        potential: float,
        inhibitory_gaba: bool = False,
        emotion_vector: list[float] | None = None,
        payload: Any = None,
    ) -> SynapticSpike:
        spike = SynapticSpike(
            source_neuron=source_neuron,
            target_cluster=target_cluster,
            potential=potential,
            inhibitory_gaba=inhibitory_gaba,
            emotion_vector=emotion_vector or [0.0, 0.0, 0.0, 0.0],
            payload=payload,
            timestamp=self._clock(),
        )
        with self._lock:
            self._spike_ring.append(spike)
        self.publish(
            f"synapse.{source_neuron}.{target_cluster}",
            {
                "source": source_neuron,
                "target": target_cluster,
                "potential": potential,
                "gaba": inhibitory_gaba,
                "emotion": spike.emotion_vector,
            },
            origin="synapse",
        )
        return spike

    def pop_spike(self) -> SynapticSpike | None:
        with self._lock:
            return self._spike_ring.popleft() if self._spike_ring else None

    def publish(self, topic: str, payload: dict | None = None, origin: str = "supervisor", retain: bool = False,
                schema: str = SCHEMA_VERSION) -> Envelope:
        if not valid_topic(topic):
            raise BusError(f"invalid topic: {topic!r}")
        if not valid_origin(origin):
            raise BusError(f"invalid origin: {origin!r}")
        body = dict(payload or {})
        if len(json.dumps(body, default=str)) > MAX_PAYLOAD:
            raise BusError("payload too large")
        envelope = Envelope(uuid.uuid4().hex, topic, self._clock(), origin, schema, body, retain)
        with self._lock:
            self.published += 1
            if retain:
                if not body:
                    self._retained.pop(topic, None)
                elif topic in self._retained or len(self._retained) < MAX_RETAINED:
                    self._retained[topic] = envelope
            targets = [self._subs[sid] for sid in self._router.route(topic)]
        for sub in targets:
            self._deliver(sub, envelope)
        return envelope

    def _deliver(self, sub: Subscription, envelope: Envelope) -> None:
        try:
            result = sub.callback(envelope)
            if inspect.isawaitable(result):
                self._schedule(result)
        except Exception as exc:
            self.failures += 1
            log.warning("subscriber of %s failed on %s: %s", sub.pattern, envelope.topic, exc)

    def _schedule(self, coroutine) -> None:
        try:
            asyncio.get_running_loop().create_task(coroutine)
        except RuntimeError:
            if self._loop is not None and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(coroutine, self._loop)
            else:
                coroutine.close()

    def retained(self, pattern: str = ">") -> list[Envelope]:
        with self._lock:
            return [e for t, e in sorted(self._retained.items()) if matches(pattern, t)]

    def announce(self, module: str, capabilities: list[str] | None = None, status: str = "ready",
                  ttl: float = DISCOVERY_TTL, info: dict | None = None) -> None:
        now = self._clock()
        with self._lock:
            known = module in self._modules
            self._modules[module] = {"module": module, "capabilities": sorted(set(capabilities or [])), "status": status,
                                     "seen": now, "ttl": ttl, "info": dict(info or {})}
            record = dict(self._modules[module])
        self.publish(f"system.discovery.{'heartbeat' if known else 'announce'}", record, origin=module)
        self.publish(f"system.module.{module}", record, origin=module, retain=True)

    def expire(self) -> list[str]:
        now = self._clock()
        with self._lock:
            lost = [m for m, r in self._modules.items() if now - r["seen"] > r["ttl"]]
            for module in lost:
                del self._modules[module]
        for module in lost:
            self.publish("system.discovery.lost", {"module": module}, origin="bus")
            self.publish(f"system.module.{module}", {}, origin="bus", retain=True)
        return lost

    def modules(self, capability: str = "") -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._modules.values() if not capability or capability in r["capabilities"]]

    def stats(self) -> dict:
        with self._lock:
            return {
                "engine": ENGINE,
                "published": self.published,
                "failures": self.failures,
                "subscribers": len(self._subs),
                "retained": len(self._retained),
                "modules": len(self._modules),
                "spike_queue_len": len(self._spike_ring),
            }

    async def run(self) -> None:
        self.bind_loop(asyncio.get_running_loop())
        while True:
            await asyncio.sleep(15)
            self.expire()


nuxiva_bus = NuxivaBus()
