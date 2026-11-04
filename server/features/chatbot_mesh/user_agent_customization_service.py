import os
import json
import time
import logging
from typing import Dict, Any, List
from server.config.env import settings
from server.core.agent_registry.catalog import DEFAULT_AGENT_CATALOG
from server.features.chatbot_mesh.chatbot_models import (
    UserAgentPersonalization,
    ChatbotTone,
    ChatHistoryRecord,
)

logger = logging.getLogger("nuxiva.user_agent_customization")

class UserAgentCustomizationService:
    """
    Gestisce la matrice di personalizzazione Utente x Agente.
    Ogni persona della casa o dell'azienda possiede la propria configurazione
    personalizzata per ciascun agente (tono, istruzioni private, widget abilitati, tool).
    Salvato in DATA_DIR/user_agent_configs/<user_id>/<agent_id>.json.
    Non viene mai sovrascritto dagli aggiornamenti di sistema.
    """
    _instance = None

    def __new__(cls) -> "UserAgentCustomizationService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._base_dir = os.path.join(settings.DATA_DIR, "user_agent_configs")
            os.makedirs(cls._instance._base_dir, exist_ok=True)
        return cls._instance

    def _get_user_dir(self, user_id: str) -> str:
        user_dir = os.path.join(self._base_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _get_config_path(self, user_id: str, agent_id: str) -> str:
        return os.path.join(self._get_user_dir(user_id), f"{agent_id}.json")

    def _get_history_path(self, user_id: str, agent_id: str) -> str:
        return os.path.join(self._get_user_dir(user_id), f"{agent_id}_history.json")

    def get_personalization(self, user_id: str, agent_id: str) -> UserAgentPersonalization:
        config_path = self._get_config_path(user_id, agent_id)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return UserAgentPersonalization(**data)
            except Exception as e:
                logger.error(f"Errore lettura config per user {user_id} e agente {agent_id}: {e}")

        # Configurazione dinamica tramite Dynamic Scanner
        from server.core.agent_registry.dynamic_scanner import dynamic_scanner
        spec = DEFAULT_AGENT_CATALOG.get(agent_id)
        scanned_tools = [t.id for t in dynamic_scanner.scan_tools()]
        scanned_widgets = [w.id for w in dynamic_scanner.scan_widgets()]

        default_tools = spec.tools if spec and spec.tools else scanned_tools[:5]
        default_widgets = spec.widgets if spec and spec.widgets else scanned_widgets[:4]

        nickname = spec.name if spec else agent_id.replace("_", " ").title()
        persona = UserAgentPersonalization(
            user_id=user_id,
            agent_id=agent_id,
            custom_nickname=nickname,
            preferred_tone=ChatbotTone.FRIENDLY,
            custom_persona_prompt="",
            custom_knowledge_notes="",
            allowed_tools=default_tools,
            enabled_widgets=default_widgets,
            preferred_language=settings.NUXIVA_DEFAULT_LANGUAGE,
        )
        self.save_personalization(persona)
        return persona

    def save_personalization(self, config: UserAgentPersonalization) -> None:
        config.updated_at = time.time()
        config_path = self._get_config_path(config.user_id, config.agent_id)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"Personalizzazione salvata per {config.user_id} x {config.agent_id}")
        except Exception as e:
            logger.error(f"Errore salvataggio personalizzazione: {e}")

    def list_user_personalizations(self, user_id: str) -> List[UserAgentPersonalization]:
        user_dir = self._get_user_dir(user_id)
        results: List[UserAgentPersonalization] = []
        for filename in os.listdir(user_dir):
            if filename.endswith(".json") and not filename.endswith("_history.json"):
                agent_id = filename[:-5]
                results.append(self.get_personalization(user_id, agent_id))
        return results

    def append_chat_history(self, user_id: str, agent_id: str, record: ChatHistoryRecord) -> None:
        history_path = self._get_history_path(user_id, agent_id)
        history: List[Dict[str, Any]] = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        
        history.append(record.model_dump())
        # Mantieni ultimi 100 turni per cronologia privata
        if len(history) > 100:
            history = history[-100:]

        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Errore salvataggio cronologia chat per {user_id} x {agent_id}: {e}")

    def get_chat_history(self, user_id: str, agent_id: str, limit: int = 50) -> List[ChatHistoryRecord]:
        history_path = self._get_history_path(user_id, agent_id)
        if not os.path.exists(history_path):
            return []
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = [ChatHistoryRecord(**item) for item in data]
                return records[-limit:]
        except Exception as e:
            logger.error(f"Errore lettura cronologia: {e}")
            return []

user_agent_customization_service = UserAgentCustomizationService()
