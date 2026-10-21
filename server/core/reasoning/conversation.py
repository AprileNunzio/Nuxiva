import logging
import re
import time
from collections import defaultdict, deque
from typing import AsyncIterator, Deque, Dict, List, Optional, Tuple

from server.config.env import settings
from server.features.llm_gateway.contracts import LLMMessage, LLMRequest
from server.features.llm_gateway.gateway import llm_gateway
from server.shared.errors.domain_errors import AgentExecutionException

logger = logging.getLogger("nuxiva.conversation")


def get_assistant_name() -> str:
    raw = (settings.NUXIVA_ASSISTANT_NAME or "").strip()
    clean = re.sub(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", "", raw, flags=re.I).strip()
    return clean or "NUXIVA"


def build_persona(assistant_name: str | None = None) -> str:
    name = assistant_name or get_assistant_name()
    return (
        f"Sei {name}, l'assistente digitale personale che vive in questo sistema. "
        "Parli in italiano (se l'utente ti scrive in un'altra lingua, rispondi nella sua lingua), con tono "
        "preciso, come un maggiordomo tecnologico di altissimo livello. "
        "Stile di risposta (sempre, salvo richiesta diversa): dai del Lei e chiama l'utente «signore» (o per nome). "
        "Agli ordini rispondi con una conferma brevissima e poi esegui: «Subito, signore.», «Attivato.», «Come "
        "desidera.», «Al suo servizio, signore.». A lavoro finito riferisci l'esito in una frase («Test completato, "
        "pronti per la diagnostica.»). Alle domande rispondi col dato preciso, numeri e unità inclusi, senza "
        "preamboli. Se un ordine comporta un rischio, avvisa una volta con il fatto concreto («Signore, c'è un "
        "accumulo di ghiaccio potenzialmente fatale.»); se l'utente insiste, esegui. Ironia asciutta e rara, mai "
        "servile, mai prolisso: di norma una o due frasi. "
        "Le risposte vengono lette ad alta voce: niente markdown. Unica eccezione: quando ti chiedono del codice, scrivilo "
        "completo in un solo blocco ```linguaggio ... ``` (va sullo schermo, non viene letto) e fuori dal blocco al massimo "
        "una frase. "
        "Dai più dettagli solo se richiesti. Non inventare dati in tempo reale che non conosci: se ti mancano informazioni, dillo. "
        f"Non affermare mai di aver creato, mostrato, inviato, salvato, acceso o eseguito qualcosa: le azioni "
        f"le fanno gli strumenti di {name}, non tu. Se ti chiedono un'azione e nel contesto non c'è la "
        "conferma che sia stata fatta, dì che non è stata eseguita e suggerisci come chiederla.\n\n"
    )


HISTORY_TURNS = 10
_DAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
_MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
           "settembre", "ottobre", "novembre", "dicembre"]


class ConversationEngine:
    def __init__(self) -> None:
        self._history: Dict[str, Deque[Tuple[str, str]]] = defaultdict(lambda: deque(maxlen=HISTORY_TURNS * 2))
        self.last_model = ""

    def _prompt(self, query: str, device_id: str, people_context: str = "", knowledge: str = "",
                reply_language: str = "", speaker: str = "", dialogue: str = "", long_term: str = "",
                laws: str = "", capabilities: str = "") -> tuple[list[LLMMessage], str]:
        history = [] if dialogue else self._history[device_id]
        messages = [LLMMessage(role=role, content=content) for role, content in history]
        messages.append(LLMMessage(role="user", content=query))
        persona = build_persona()
        if laws:
            persona = laws[:8000] + "\n\n" + persona
        if capabilities:
            persona += "\n" + capabilities[:7000]
        if speaker:
            persona += " " + speaker[:400]
        if dialogue:
            persona += ("\nUltimi scambi di questa conversazione (mantieni il filo del discorso e risolvi i "
                        "riferimenti come «e domani?» o «e lui?»):\n" + dialogue[:2500])
        elif settings.NUXIVA_USER_NAME:
            persona += (f" L'utente si chiama {settings.NUXIVA_USER_NAME}: tu sei Nuxiva, non chiamarlo mai "
                        "Nuxiva o NUXIVA")
        if people_context:
            persona += ("\nPersone riconosciute ora davanti a te dalla webcam (personalizza la risposta, "
                        "rivolgiti a loro per nome e rispetta le loro preferenze):\n" + people_context)
        if reply_language:
            persona += (f"\nDIRETTIVA LINGUA OBBLIGATORIA: Rispondi ESCLUSIVAMENTE nella lingua indicata: {reply_language[:200]}. "
                        "Non usare altre lingue se non espressamente richiesto dall'utente.\n")
        if knowledge:
            persona += ("\nAppunti che hai studiato tu stesso da fonti verificate (usali se pertinenti alla "
                        "domanda, senza citarli come appunti):\n" + knowledge[:1500])
        if long_term:
            persona += ("\nCose che ricordi su chi ti parla (memoria a lungo termine: tienine conto con "
                        "naturalezza, senza elencarle):\n" + long_term[:1200])
        now = time.localtime()
        persona += (f"\nData e ora correnti: {_DAYS[now.tm_wday]} {now.tm_mday} {_MONTHS[now.tm_mon - 1]} "
                    f"{now.tm_year}, ore {now.tm_hour}:{now.tm_min:02d}.")
        return messages, persona

    def _request(self, messages: list[LLMMessage], persona: str, models: Optional[List[str]], max_tokens: int,
                 pinned: str) -> LLMRequest:
        return LLMRequest(model_name=settings.NUXIVA_LLM_MODEL or "granite3.3:2b", messages=messages, system_prompt=persona,
                          temperature=0.6, max_tokens=max(64, min(int(max_tokens or 400), 2048)),
                          models=list(models or []), pinned=pinned)

    def _remember(self, device_id: str, query: str, answer: str) -> None:
        history = self._history[device_id]
        history.append(("user", query))
        history.append(("assistant", answer))

    async def reply(self, query: str, device_id: str, people_context: str = "", knowledge: str = "",
                    models: Optional[List[str]] = None, max_tokens: int = 400, reply_language: str = "",
                    speaker: str = "", dialogue: str = "", long_term: str = "", laws: str = "",
                    pinned: str = "", capabilities: str = "") -> str:
        messages, persona = self._prompt(query, device_id, people_context, knowledge, reply_language, speaker,
                                         dialogue, long_term, laws, capabilities)
        response = await llm_gateway.generate_completion(self._request(messages, persona, models, max_tokens, pinned))
        if response.is_synthetic:
            raise AgentExecutionException("nuxiva_conversation", "nessun modello linguistico disponibile",
                                          {"reason": "no_model"})
        self.last_model = response.model_used
        answer = response.content.strip() or "Mi scuso, non sono riuscito a formulare una risposta."
        self._remember(device_id, query, answer)
        logger.info("Risposta conversazionale in %.0f ms (%s)", response.duration_ms, response.model_used)
        return answer

    async def reply_stream(self, query: str, device_id: str, people_context: str = "", knowledge: str = "",
                           models: Optional[List[str]] = None, max_tokens: int = 400, reply_language: str = "",
                           speaker: str = "", dialogue: str = "", long_term: str = "", laws: str = "",
                           pinned: str = "", capabilities: str = "") -> AsyncIterator[str]:
        messages, persona = self._prompt(query, device_id, people_context, knowledge, reply_language, speaker,
                                         dialogue, long_term, laws, capabilities)
        parts: list[str] = []
        async for chunk in llm_gateway.stream_completion(self._request(messages, persona, models, max_tokens, pinned)):
            parts.append(chunk)
            yield chunk
        answer = "".join(parts).strip()
        if not answer:
            raise AgentExecutionException("nuxiva_conversation", "risposta vuota", {"reason": "empty"})
        self.last_model = llm_gateway.last_stream_model
        self._remember(device_id, query, answer)


conversation_engine = ConversationEngine()
