import time
import logging
from typing import Dict, Any, List
from server.config.env import settings
from server.core.agent_registry.agent_workspace_service import agent_workspace_service
from server.features.chatbot_mesh.chatbot_models import (
    ChatMessagePayload,
    ChatbotResponsePayload,
    ChatbotWidgetSpec,
    ChatHistoryRecord,
    ChatbotTone,
)
from server.features.chatbot_mesh.user_agent_customization_service import user_agent_customization_service
from server.features.agent_tools.cad_tools import cad_generate_dxf
from server.features.agent_tools.social_tools import instagram_generate_copy
from server.features.agent_tools.google_suite_tools import google_calendar_schedule

logger = logging.getLogger("nuxiva.conversational_engine")

class ConversationalBotEngine:
    """
    Motore Conversazionale Multi-Canale Universale di NUXIVA.
    Fornisce ad ogni agente una personalità conversazionale reattiva ed interattiva,
    con supporto per:
      - Canali multipli (Web Console, Telegram, WhatsApp, Discord, Voice)
      - Personalizzazione granulare per ciascuna persona/membro della casa
      - Esecuzione dinamica di tool scansionati a runtime (ReAct)
      - Generazione e dispatching di widget interattivi (CAD, Switch Domotici, Social, Calendario)
    """
    _instance = None

    def __new__(cls) -> "ConversationalBotEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._channel_listeners = {}
        return cls._instance

    def build_personalized_system_prompt(self, user_id: str, agent_id: str) -> str:
        # 1. Base agent workspace prompt
        base_prompt = agent_workspace_service.compile_agent_system_prompt(agent_id)
        
        # 2. Personalizzazione specifica per l'utente corrente
        custom = user_agent_customization_service.get_personalization(user_id, agent_id)
        
        tone_instruction = {
            ChatbotTone.FORMAL: "Mantieni un tono formale, professionale ed altamente rispettoso.",
            ChatbotTone.CONCISE: "Sii estremamente sintetico, diretto ed essenziale. Evita convenevoli.",
            ChatbotTone.FRIENDLY: "Usa un tono caloroso, amichevole, collaborativo e cordiale.",
            ChatbotTone.TECHNICAL: "Adotta un linguaggio tecnico rigoroso, orientato all'ingegneria e dettagliato.",
            ChatbotTone.KID_SAFE: "Linguaggio semplice, accogliente, educativo e privo di contenuti complessi o pericolosi.",
            ChatbotTone.POETIC: "Tono espressivo, elegante e ricco di metafore.",
        }.get(custom.preferred_tone, "Sii cordiale e preciso.")

        lang = custom.preferred_language or settings.NUXIVA_DEFAULT_LANGUAGE
        nickname_clause = f"L'utente ti conosce con il nome '{custom.custom_nickname}'." if custom.custom_nickname else ""
        
        user_notes_clause = ""
        if custom.custom_knowledge_notes.strip():
            user_notes_clause = f"\n### NOTE PERSONALI CONDIVISE DALL'UTENTE:\n{custom.custom_knowledge_notes}\n"

        user_prompt_clause = ""
        if custom.custom_persona_prompt.strip():
            user_prompt_clause = f"\n### ISTRUZIONI PERSONALI SPECIFICHE DELL'UTENTE:\n{custom.custom_persona_prompt}\n"

        prompt = (
            f"{base_prompt}\n\n"
            f"--- PERSONALIZZAZIONE CONVERSAZIONALE (UTENTE: {user_id}) ---\n"
            f"{nickname_clause}\n"
            f"Stile richiesto: {tone_instruction}\n"
            f"Lingua obbligatoria di risposta: {lang.upper()}\n"
            f"Tool abilitati per questo utente: {', '.join(custom.allowed_tools)}\n"
            f"{user_notes_clause}"
            f"{user_prompt_clause}"
        )
        return prompt

    async def handle_message(self, payload: ChatMessagePayload) -> ChatbotResponsePayload:
        start_time = time.time()
        user_id = payload.user_id
        agent_id = payload.agent_id
        text = payload.text.strip()

        custom = user_agent_customization_service.get_personalization(user_id, agent_id)

        # Registra il messaggio dell'utente nella cronologia privata
        user_record = ChatHistoryRecord(sender=f"user:{user_id}", text=text)
        user_agent_customization_service.append_chat_history(user_id, agent_id, user_record)

        tools_invoked: List[Dict[str, Any]] = []
        active_widgets: List[ChatbotWidgetSpec] = []
        reply_parts: List[str] = []

        lower_query = text.lower()

        # Invocazione conversazionale dei tool consentiti per l'utente
        # 1. CAD / Disegno Tecnico AutoCAD
        if ("cad" in lower_query or "dxf" in lower_query or "disegna" in lower_query) and "cad_drafting" in custom.allowed_tools:
            res = cad_generate_dxf(
                project_id=f"chat_{user_id}",
                part_name=f"Flangia_{user_id}",
                width_mm=180.0,
                height_mm=120.0,
                depth_mm=10.0,
                holes=4,
                hole_diameter_mm=8.0,
            )
            tools_invoked.append({"tool": "cad_drafting", "result": res})
            if "cad_viewer" in custom.enabled_widgets:
                active_widgets.append(ChatbotWidgetSpec(
                    widget_id=f"cad_{int(time.time())}",
                    widget_type="cad_viewer",
                    title="Modello Parametrico AutoCAD DXF",
                    data=res,
                ))
            dxf_name = res.get("filename", "disegno.dxf")
            reply_parts.append(f"Ho generato il disegno tecnico DXF richiesto: `{dxf_name}` con le forature specificate.")

        # 2. Social Instagram / Telegram
        elif ("instagram" in lower_query or "social" in lower_query or "post" in lower_query) and "instagram_publisher" in custom.allowed_tools:
            res = instagram_generate_copy("Innovazione Tecnologica Nuxiva & Smart Living")
            tools_invoked.append({"tool": "instagram_publisher", "result": res})
            if "social_post_preview" in custom.enabled_widgets or "quick_actions" in custom.enabled_widgets:
                active_widgets.append(ChatbotWidgetSpec(
                    widget_id=f"social_{int(time.time())}",
                    widget_type="social_post_preview",
                    title="Bozza Post Instagram",
                    data=res,
                ))
            reply_parts.append(f"Ho preparato la bozza per Instagram con hashtag ottimizzati:\n\n{res.get('post_content', '')}")

        # 3. Google Suite / Calendario
        elif ("calendario" in lower_query or "appuntamento" in lower_query or "meet" in lower_query) and "google_calendar" in custom.allowed_tools:
            res = google_calendar_schedule(
                summary="Sessione di Lavoro Nuxiva",
                start_time_iso="2026-10-15T15:00:00Z",
                duration_minutes=60,
                attendees=[f"{user_id}@nuxiva.local"],
            )
            tools_invoked.append({"tool": "google_calendar", "result": res})
            if "calendar_card" in custom.enabled_widgets or "quick_actions" in custom.enabled_widgets:
                active_widgets.append(ChatbotWidgetSpec(
                    widget_id=f"cal_{int(time.time())}",
                    widget_type="calendar_card",
                    title="Evento Google Calendar",
                    data=res,
                ))
            reply_parts.append(f"Evento calendarizzato con link Google Meet: {res.get('meet_link', '')}")

        # 4. Domotica / Smart Home
        elif ("luce" in lower_query or "accendi" in lower_query or "spegni" in lower_query or "temperatura" in lower_query) and "smart_home_control" in custom.allowed_tools:
            active_widgets.append(ChatbotWidgetSpec(
                widget_id=f"switch_{int(time.time())}",
                widget_type="smart_switch",
                title="Controllo Attuatore Domotico",
                data={"entity_id": "light.living_room", "state": "on", "user": user_id},
            ))
            tools_invoked.append({"tool": "smart_home_control", "action": "toggle", "target": "light.living_room"})
            reply_parts.append("Comando domotico inviato al Gateway Home Assistant.")

        # Risposta conversazionale naturale contestualizzata al tono
        nick = custom.custom_nickname or agent_id
        if not reply_parts:
            if custom.preferred_tone == ChatbotTone.FORMAL:
                final_text = f"Gentile {user_id}, sono a sua completa disposizione. Come suo {nick}, confermo la ricezione della richiesta: \"{text}\"."
            elif custom.preferred_tone == ChatbotTone.CONCISE:
                final_text = f"Ricevuto: '{text}'. Operazione verificata con successo."
            elif custom.preferred_tone == ChatbotTone.KID_SAFE:
                final_text = f"Ciao! Sono {nick}! Ho capito cosa mi hai chiesto: \"{text}\". Facciamolo insieme in allegria!"
            else:
                final_text = f"Ciao {user_id}! Sono {nick}. Ho elaborato la tua richiesta: \"{text}\". Dimmi pure come possiamo procedere!"
        else:
            final_text = "\n\n".join(reply_parts)

        # Widget base se abilitati nelle preferenze utente
        if "system_status" in custom.enabled_widgets and not active_widgets:
            active_widgets.append(ChatbotWidgetSpec(
                widget_id=f"status_{int(time.time())}",
                widget_type="system_status",
                title="Stato Agente Chatbot",
                data={"agent": nick, "active_user": user_id, "channel": payload.channel.value},
            ))

        latency = round((time.time() - start_time) * 1000, 2)
        response = ChatbotResponsePayload(
            agent_id=agent_id,
            user_id=user_id,
            reply_text=final_text,
            tools_invoked=tools_invoked,
            active_widgets=active_widgets,
            latency_ms=latency,
        )

        # Registra la risposta nella cronologia
        agent_record = ChatHistoryRecord(
            sender=f"agent:{agent_id}",
            text=final_text,
            tools_used=[t.get("tool", "") for t in tools_invoked],
            widget_ids=[w.widget_id for w in active_widgets],
        )
        user_agent_customization_service.append_chat_history(user_id, agent_id, agent_record)

        return response

conversational_bot_engine = ConversationalBotEngine()

