import logging
import asyncio
from typing import Callable, Awaitable, List

from server.core.event_sourcing.universal_space import UniversalObservation, UniversalAction
from server.features.continuous_learning.babbling_engine import babbling_engine

logger = logging.getLogger("nuxiva.sensory_bus")

class SensoryBusCoordinator:
    """
    Ingresso unico per tutti gli stimoli sensoriali.
    Che si tratti di un frame della webcam, di un pacchetto di rete, o di audio,
    tutto passa da qui sotto forma di UniversalObservation.
    """
    def __init__(self):
        self.observation_queue: asyncio.Queue = asyncio.Queue()
        self.action_subscribers: List[Callable[[UniversalAction], Awaitable[None]]] = []
        self._running = False

    def start(self):
        if not self._running:
            self._running = True
            asyncio.create_task(self._process_queue())
            logger.info("Sensory Bus Coordinator avviato.")

    def stop(self):
        self._running = False

    async def push_observation(self, observation: UniversalObservation):
        """Invia un'osservazione universale nella coda del bus."""
        await self.observation_queue.put(observation)
        logger.debug(f"Observation {observation.id} [{observation.modality}] accodata.")

    async def emit_action(self, action: UniversalAction):
        """Invia un'azione astratta verso l'attuatore reale."""
        logger.info(f"Emissione Action {action.id} verso [{action.target_modality}].")
        for sub in self.action_subscribers:
            try:
                await sub(action)
            except Exception as e:
                logger.error(f"Errore nel subscriber dell'actuator per {action.target_modality}: {e}")

    def subscribe_to_actions(self, callback: Callable[[UniversalAction], Awaitable[None]]):
        """Registra un hardware driver o attuatore per ricevere comandi."""
        self.action_subscribers.append(callback)

    async def _process_queue(self):
        while self._running:
            observation: UniversalObservation = await self.observation_queue.get()
            try:
                # 1. Prova prima il Fast Path (System 1)
                # Nel sistema reale, si fa un check su semantic_cache
                logger.debug(f"Routing observation {observation.id} al System 1...")
                
                # Mock della logica di routing:
                # Se è un frame visivo di cui non sa nulla, andrà al BabblingEngine.
                # Per ora dirottiamo tutto quello che non è puro "text" di dominio noto
                # al motore esplorativo.
                if observation.modality in ["vision", "network_packet", "usb_interrupt", "unknown"]:
                    # Fallback al Motore di Esplorazione se il System 1 non ha mappe motorie pronte
                    await babbling_engine.handle_unknown_stimulus(observation, sensory_bus_ref=self)
                elif observation.modality == "home_assistant":
                    # FASE 4: Inoltro eventi domotici al motore proattivo (System 2)
                    from server.core.planner.proactive_engine import proactive_engine
                    await proactive_engine.analyze_event(observation)
                elif observation.modality == "system_alert":
                    # AUTORECOVERY / SELF-HEALING DETERMINISTICO
                    # Se il LLM è giù, non possiamo usare il LLM per ragionare su come riavviarlo.
                    # Dobbiamo agire con riflesso incondizionato (System 1 puro).
                    alert_type = observation.raw_data.get("alert_type")
                    service = observation.raw_data.get("service")
                    
                    if alert_type == "service_down" and service == "ollama":
                        from server.config.env import settings
                        if getattr(settings, "LLM_PROVIDER", "ollama").lower() != "ollama":
                            logger.info("SensoryBus: Allarme Ollama ignorato in quanto il provider configurato è esterno/cloud.")
                        else:
                            logger.critical("SensoryBus: Ricevuto allarme critico (OLLAMA DOWN). Innesco riflesso incondizionato di auto-ripristino...")
                            import subprocess
                            import sys
                            if sys.platform != "win32":
                                try:
                                    subprocess.Popen(["sudo", "-n", "systemctl", "restart", "ollama"])
                                    logger.info("Comando di restart Ollama inviato con successo dal riflesso di emergenza.")
                                except Exception as e:
                                    logger.error(f"Tentativo restart Ollama non riuscito: {e}")
                else:
                    # Passaggio normale al dispatcher
                    logger.debug(f"Gestione standard System 1 per {observation.modality}")
                    
            except Exception as e:
                logger.error(f"Errore durante l'elaborazione dell'Observation {observation.id}: {e}")
            finally:
                self.observation_queue.task_done()

sensory_bus = SensoryBusCoordinator()
