from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from server.core.agent_registry.catalog import DEFAULT_AGENT_CATALOG
from server.core.agent_registry.forge import CustomAgentForge
from server.core.agent_registry.dynamic_scanner import dynamic_scanner
from server.features.chatbot_mesh.chatbot_models import (
    ChatMessagePayload,
    ChatbotResponsePayload,
    UserAgentPersonalization,
    ChatHistoryRecord,
)
from server.features.chatbot_mesh.user_agent_customization_service import user_agent_customization_service
from server.features.chatbot_mesh.conversational_engine import conversational_bot_engine

chatbot_router = APIRouter(prefix="/chatbot", tags=["Chatbot & Conversational Mesh"])

@chatbot_router.get("/agents")
async def list_conversational_agents():
    """
    Elenco dinamico di tutti gli agenti/chatbot disponibili,
    scansionando sia il catalogo base che gli agenti custom creati dall'utente.
    Nessun dato hardcodato fisso.
    """
    forge = CustomAgentForge()
    all_agents = forge.list_all_agents()
    agents = []
    for spec in all_agents:
        agents.append({
            "agent_id": spec.id,
            "name": spec.name,
            "role_category": spec.role_category,
            "avatar_icon": spec.avatar_icon,
            "description": spec.description,
            "tools": spec.tools,
            "widgets": spec.widgets,
            "is_custom": spec.is_custom,
            "is_chatbot": True,
        })
    return {"status": "success", "agents": agents}

@chatbot_router.get("/widgets/catalog")
async def list_available_widgets():
    """
    Catalogo ottenuto dinamicamente dallo scansionatore universale (DynamicScannerRegistry).
    Rileva automaticamente tutti i widget dei moduli di sistema e dei tool attivi.
    """
    widgets = dynamic_scanner.scan_widgets()
    return {"status": "success", "widgets": [w.model_dump() for w in widgets]}

@chatbot_router.get("/tools/catalog")
async def list_available_tools():
    """
    Catalogo ottenuto dinamicamente dallo scansionatore universale.
    Rileva a runtime tutti gli strumenti Python nei moduli o nei plugin.
    """
    tools = dynamic_scanner.scan_tools()
    return {"status": "success", "tools": [t.model_dump() for t in tools]}

@chatbot_router.get("/users/{user_id}/agents/{agent_id}/config")
async def get_user_agent_config(user_id: str, agent_id: str):
    """Restituisce le impostazioni personalizzate del singolo utente per questo specifico agente."""
    config = user_agent_customization_service.get_personalization(user_id, agent_id)
    return {"status": "success", "config": config.model_dump()}

@chatbot_router.post("/users/{user_id}/agents/{agent_id}/config")
async def save_user_agent_config(user_id: str, agent_id: str, payload: UserAgentPersonalization):
    """Salva la personalizzazione (tono, istruzioni, widget, tool) per questo utente e agente."""
    if payload.user_id != user_id or payload.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Mancata corrispondenza tra URL e payload")
    user_agent_customization_service.save_personalization(payload)
    return {"status": "success", "saved": payload.model_dump()}

@chatbot_router.post("/chat")
async def send_chat_message(payload: ChatMessagePayload):
    """Invia un messaggio all'agente scelto nel contesto dell'utente, eseguendo tool e generando widget."""
    response = await conversational_bot_engine.handle_message(payload)
    return {"status": "success", "response": response.model_dump()}

@chatbot_router.get("/users/{user_id}/agents/{agent_id}/history")
async def get_chat_history(user_id: str, agent_id: str, limit: int = 50):
    """Restituisce la cronologia dei messaggi privati tra questo utente e questo agente."""
    history = user_agent_customization_service.get_chat_history(user_id, agent_id, limit=limit)
    return {"status": "success", "history": [h.model_dump() for h in history]}
