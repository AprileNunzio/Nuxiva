import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from server.config.env import settings
from server.core.agent_registry.catalog import DEFAULT_AGENT_CATALOG, AgentCapabilitySpec

logger = logging.getLogger("nuxiva.agent_workspace")

class AgentWorkspaceProfile(BaseModel):
    agent_id: str
    name: str
    role_category: str
    avatar_icon: str
    preferred_model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 1500
    primary_widget: str = ""
    allowed_widgets: List[str] = Field(default_factory=list)
    custom_tools: List[str] = Field(default_factory=list)
    total_invocations: int = 0
    successful_tasks: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

class AgentKnowledgeDoc(BaseModel):
    filename: str
    title: str
    content: str
    size_bytes: int = 0
    updated_at: float = Field(default_factory=time.time)

class AgentWorkspaceDetail(BaseModel):
    profile: AgentWorkspaceProfile
    instructions: str
    knowledge_docs: List[AgentKnowledgeDoc] = Field(default_factory=list)
    custom_tools_code: Dict[str, str] = Field(default_factory=dict)
    workspace_dir: str

class AgentWorkspaceService:
    """
    Gestisce la directory isolata e protetta per ogni singolo agente in DATA_DIR/agents/<agent_id>/.
    Nessun aggiornamento di Nuxiva sovrascrive o cancella questa directory.
    Contiene:
      - profile.json: configurazioni del modello, parametri e widget.
      - instructions.md: insegnamenti, prompt operativo, stile e vincoli.
      - knowledge/: archivio di documenti, dispense e nozioni fornite dall'utente.
      - tools/: script di tool personalizzati dedicati solo a questo agente.
    """
    _instance = None

    def __new__(cls) -> "AgentWorkspaceService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._base_dir = os.path.join(settings.DATA_DIR, "agents")
            os.makedirs(cls._instance._base_dir, exist_ok=True)
            cls._instance._ensure_default_workspaces()
        return cls._instance

    def _agent_dir(self, agent_id: str) -> str:
        clean_id = agent_id.lower().replace(" ", "_")
        d = os.path.join(self._base_dir, clean_id)
        os.makedirs(d, exist_ok=True)
        os.makedirs(os.path.join(d, "knowledge"), exist_ok=True)
        os.makedirs(os.path.join(d, "tools"), exist_ok=True)
        return d

    def _ensure_default_workspaces(self) -> None:
        # Inizializza le directory per tutti gli agenti di default se non esistono
        for agent_id, spec in DEFAULT_AGENT_CATALOG.items():
            self._init_workspace_if_missing(spec)

        # Inizializza anche l'agente dedicato a Windows e Remote Control
        windows_spec = AgentCapabilitySpec(
            id="windows_system_agent",
            name="Windows Power & System Specialist",
            role_category="engineering",
            avatar_icon="monitor",
            description="Specialista assoluto per Windows: automazione desktop, PowerShell, registro, processi, app e finestre.",
            system_prompt=(
                "Sei lo specialista Windows di NUXIVA. Conosci l'ecosistema Windows, PowerShell, "
                "le API Win32, la gestione delle finestre, i comandi di sistema e l'automazione dei processi."
            ),
            tools=["windows_powershell_exec", "windows_window_focus", "windows_process_monitor"],
            widgets=["windows_desktop_control_widget", "system_health"],
        )
        self._init_workspace_if_missing(windows_spec)

    def _init_workspace_if_missing(self, spec: AgentCapabilitySpec) -> None:
        d = self._agent_dir(spec.id)
        profile_file = os.path.join(d, "profile.json")
        instructions_file = os.path.join(d, "instructions.md")

        if not os.path.exists(profile_file):
            profile = AgentWorkspaceProfile(
                agent_id=spec.id,
                name=spec.name,
                role_category=spec.role_category,
                avatar_icon=spec.avatar_icon,
                primary_widget=spec.widgets[0] if spec.widgets else "",
                allowed_widgets=spec.widgets,
                custom_tools=[],
            )
            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(profile.model_dump(), f, indent=2)

        if not os.path.exists(instructions_file):
            with open(instructions_file, "w", encoding="utf-8") as f:
                f.write(spec.system_prompt)

    def get_workspace(self, agent_id: str) -> Optional[AgentWorkspaceDetail]:
        d = self._agent_dir(agent_id)
        profile_file = os.path.join(d, "profile.json")
        instructions_file = os.path.join(d, "instructions.md")

        if not os.path.exists(profile_file):
            # Crea al volo se è un nuovo agente
            spec = AgentCapabilitySpec(
                id=agent_id,
                name=agent_id.replace("_", " ").title(),
                role_category="custom",
                avatar_icon="cpu",
                description=f"Workspace per {agent_id}",
                system_prompt="Sei un agente specializzato autonomo di Nuxiva.",
            )
            self._init_workspace_if_missing(spec)

        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                profile = AgentWorkspaceProfile(**json.load(f))
        except Exception:
            profile = AgentWorkspaceProfile(
                agent_id=agent_id,
                name=agent_id,
                role_category="general",
                avatar_icon="cpu",
            )

        instructions = ""
        if os.path.exists(instructions_file):
            with open(instructions_file, "r", encoding="utf-8") as f:
                instructions = f.read()

        # Leggi file di knowledge
        knowledge_docs: List[AgentKnowledgeDoc] = []
        k_dir = os.path.join(d, "knowledge")
        if os.path.exists(k_dir):
            for fname in os.listdir(k_dir):
                fpath = os.path.join(k_dir, fname)
                if os.path.isfile(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8") as kf:
                            content = kf.read()
                            knowledge_docs.append(AgentKnowledgeDoc(
                                filename=fname,
                                title=fname.replace(".md", "").replace("_", " ").title(),
                                content=content,
                                size_bytes=len(content.encode("utf-8")),
                                updated_at=os.path.getmtime(fpath),
                            ))
                    except Exception:
                        pass

        # Leggi script di custom tools
        tools_code: Dict[str, str] = {}
        t_dir = os.path.join(d, "tools")
        if os.path.exists(t_dir):
            for fname in os.listdir(t_dir):
                if fname.endswith(".py"):
                    fpath = os.path.join(t_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as tf:
                            tools_code[fname] = tf.read()
                    except Exception:
                        pass

        return AgentWorkspaceDetail(
            profile=profile,
            instructions=instructions,
            knowledge_docs=knowledge_docs,
            custom_tools_code=tools_code,
            workspace_dir=d,
        )

    def update_profile(self, agent_id: str, profile_update: AgentWorkspaceProfile) -> AgentWorkspaceProfile:
        d = self._agent_dir(agent_id)
        profile_file = os.path.join(d, "profile.json")
        profile_update.updated_at = time.time()
        with open(profile_file, "w", encoding="utf-8") as f:
            json.dump(profile_update.model_dump(), f, indent=2)
        return profile_update

    def update_instructions(self, agent_id: str, new_instructions: str) -> str:
        d = self._agent_dir(agent_id)
        instructions_file = os.path.join(d, "instructions.md")
        with open(instructions_file, "w", encoding="utf-8") as f:
            f.write(new_instructions)
        return new_instructions

    def add_or_update_knowledge(self, agent_id: str, filename: str, content: str) -> AgentKnowledgeDoc:
        d = self._agent_dir(agent_id)
        k_dir = os.path.join(d, "knowledge")
        clean_name = filename if filename.endswith((".md", ".txt")) else f"{filename}.md"
        fpath = os.path.join(k_dir, clean_name)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        return AgentKnowledgeDoc(
            filename=clean_name,
            title=clean_name.replace(".md", "").replace("_", " ").title(),
            content=content,
            size_bytes=len(content.encode("utf-8")),
            updated_at=time.time(),
        )

    def delete_knowledge(self, agent_id: str, filename: str) -> bool:
        d = self._agent_dir(agent_id)
        fpath = os.path.join(d, "knowledge", filename)
        if os.path.exists(fpath):
            os.remove(fpath)
            return True
        return False

    def add_custom_tool_script(self, agent_id: str, tool_name: str, python_code: str) -> str:
        d = self._agent_dir(agent_id)
        clean_name = tool_name if tool_name.endswith(".py") else f"{tool_name}.py"
        fpath = os.path.join(d, "tools", clean_name)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(python_code)

        # Aggiunge il tool al profilo dell'agente se non presente
        ws = self.get_workspace(agent_id)
        if ws and clean_name not in ws.profile.custom_tools:
            ws.profile.custom_tools.append(clean_name)
            self.update_profile(agent_id, ws.profile)

        return clean_name

    def record_auto_lesson(self, agent_id: str, lesson_topic: str, lesson_content: str) -> None:
        """
        Salva automaticamente una lezione o regola appresa sul campo dall'agente
        nella sua memoria permanente (auto_lessons.md). Non si perde mai tra aggiornamenti!
        """
        d = self._agent_dir(agent_id)
        fpath = os.path.join(d, "knowledge", "auto_lessons.md")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n### [{timestamp}] {lesson_topic}\n- {lesson_content}"
        
        mode = "a" if os.path.exists(fpath) else "w"
        header = "# Auto-Lessons & Regole Apprese sul Campo\n" if mode == "w" else ""
        with open(fpath, mode, encoding="utf-8") as f:
            if header:
                f.write(header)
            f.write(entry)

    def compile_agent_system_prompt(self, agent_id: str) -> str:
        """
        Compila il prompt di sistema completo fondendo instructions.md con tutti
        i documenti e le auto-lessons apprese nella cartella knowledge/.
        """
        ws = self.get_workspace(agent_id)
        if not ws:
            return "Sei un agente specializzato autonomo di Nuxiva."
        
        full_prompt = [ws.instructions]
        if ws.knowledge_docs:
            full_prompt.append("\n\n--- MEMORIA E CONOSCENZA OPERATIVA AGGIUNTIVA ---")
            for doc in ws.knowledge_docs:
                full_prompt.append(f"\n[DOCUMENTO: {doc.title}]\n{doc.content}")

        return "\n".join(full_prompt)

agent_workspace_service = AgentWorkspaceService()

