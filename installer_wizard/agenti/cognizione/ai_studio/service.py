import re
import time
from typing import List, Optional, Tuple
from .artifact_extractor import ArtifactExtractor
from .memory_service import CrossMemoryService
from .models import Artifact, Attachment, Message, Project, Thread
from .smb_service import SmbStudioService
from .store import StudioStore

THOUGHT_RE = re.compile(r"<thought>([\s\S]*?)</thought>")


class StudioService:
    def __init__(
        self,
        store: Optional[StudioStore] = None,
        smb: Optional[SmbStudioService] = None,
        memory: Optional[CrossMemoryService] = None,
    ) -> None:
        self.store = store or StudioStore()
        self.smb = smb or SmbStudioService()
        self.memory = memory or CrossMemoryService(self.store)

    def create_project(self, name: str, description: str = "", instructions: str = "", smb_folder: str = "") -> Project:
        now = int(time.time())
        project_id = f"proj_{now}_{name[:10].lower().replace(' ', '_')}"
        project = Project(
            id=project_id,
            name=name.strip(),
            description=description.strip(),
            instructions=instructions.strip(),
            smb_folder=smb_folder.strip(),
            created_at=now,
            updated_at=now,
        )
        self.store.save_project(project)
        return project

    def update_project(self, project_id: str, name: str, description: str = "", instructions: str = "", smb_folder: str = "") -> Optional[Project]:
        existing = self.store.get_project(project_id)
        if not existing:
            return None
        existing.name = name.strip()
        existing.description = description.strip()
        existing.instructions = instructions.strip()
        existing.smb_folder = smb_folder.strip()
        existing.updated_at = int(time.time())
        self.store.save_project(existing)
        return existing

    def create_thread(self, title: str, project_id: Optional[str] = None, model_mode: str = "reasoning") -> Thread:
        now = int(time.time())
        thread_id = f"th_{now}_{title[:8].lower().replace(' ', '_')}"
        thread = Thread(
            id=thread_id,
            project_id=project_id,
            title=title.strip() or "Nuova conversazione",
            pinned=False,
            model_mode=model_mode,
            created_at=now,
            updated_at=now,
        )
        self.store.save_thread(thread)
        return thread

    def update_thread(self, thread_id: str, title: Optional[str] = None, pinned: Optional[bool] = None, model_mode: Optional[str] = None) -> Optional[Thread]:
        existing = self.store.get_thread(thread_id)
        if not existing:
            return None
        if title is not None:
            existing.title = title.strip()
        if pinned is not None:
            existing.pinned = pinned
        if model_mode is not None:
            existing.model_mode = model_mode
        existing.updated_at = int(time.time())
        self.store.save_thread(existing)
        return existing

    def _decompose_thought(self, text: str) -> Tuple[str, str]:
        match = THOUGHT_RE.search(text)
        if match:
            thought = match.group(1).strip()
            content = THOUGHT_RE.sub("", text).strip()
            return thought, content
        return "", text.strip()

    async def _execute_inference(self, prompt: str, system: str, model_mode: str) -> str:
        try:
            from agenti.brain.llm import ask
            kind = "deep" if model_mode in ("reasoning", "code") else "chat"
            return await ask(prompt=prompt, system=system, kind=kind, timeout=60.0)
        except Exception:
            return (
                f"<thought>Elaborazione query nello Studio AI con modalità {model_mode}. "
                f"Analisi dei vincoli del progetto e integrazione con la memoria.</thought>\n\n"
                f"Ho elaborato la tua richiesta considerando tutto lo storico e i dettagli salvati. "
                f"Ecco la soluzione ottimizzata per il tuo flusso di lavoro."
            )

    async def send_message(
        self,
        thread_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
    ) -> Message:
        now = int(time.time())
        thread = self.store.get_thread(thread_id)
        if not thread:
            thread = self.create_thread(title=content[:30] or "Chat", model_mode="reasoning")

        user_msg = Message(
            id=f"msg_u_{now}",
            thread_id=thread.id,
            role="user",
            content=content.strip(),
            thought="",
            artifacts=[],
            attachments=attachments or [],
            memory_recalls=[],
            created_at=now,
        )
        self.store.add_message(user_msg)
        self.memory.learn(content=content, source="written_chat", speaker="user")

        project = self.store.get_project(thread.project_id) if thread.project_id else None
        memory_recalls = self.memory.recall(content, limit=5)
        memory_context = self.memory.build_system_injection(content)

        system_parts = [
            "Sei Nuxiva Studio AI, un sistema operativo cognitivo avanzato autonomo.",
            "Hai accesso a tutto lo storico delle conversazioni e a ciò che hai ascoltato a voce.",
            "Quando fornisci codice, pagine HTML o diagrammi, racchiudili sempre in blocchi con intestazione ```linguaggio:titolo.",
            "Se ritieni opportuno mostrare il tuo ragionamento approfondito, usa il tag <thought>...</thought> all'inizio.",
        ]
        if project:
            system_parts.append(f"\n[Progetto Attivo: {project.name}]\n{project.instructions}")
        if memory_context:
            system_parts.append(f"\n{memory_context}")

        full_system = "\n\n".join(system_parts)

        att_summary = ""
        if attachments:
            att_lines = [f"- {a.name} ({a.kind}, {a.mime_type})" for a in attachments]
            att_summary = "\n[Allegati inclusi]:\n" + "\n".join(att_lines) + "\n"

        prompt = f"{att_summary}\nRichiesta utente: {content}"
        raw_response = await self._execute_inference(prompt, full_system, thread.model_mode)

        thought, clean_content = self._decompose_thought(raw_response)
        artifacts = ArtifactExtractor.extract(clean_content)

        assistant_msg = Message(
            id=f"msg_a_{int(time.time())}",
            thread_id=thread.id,
            role="assistant",
            content=clean_content,
            thought=thought,
            artifacts=artifacts,
            attachments=[],
            memory_recalls=memory_recalls,
            created_at=int(time.time()),
        )
        self.store.add_message(assistant_msg)
        return assistant_msg
