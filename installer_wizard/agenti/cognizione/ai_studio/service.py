import asyncio
import logging
from typing import Any, Dict
import json
import re
import time
import uuid
from typing import List, Optional, Tuple
from .artifact_extractor import ArtifactExtractor
from .memory_service import CrossMemoryService
from .audit_service import AuditService
from .dlp_service import DlpService
from .execution_service import ExecutionService
from .knowledge_service import KnowledgeService
from .inference_service import build_prompt, infer
from .preset_service import VALID_MODES, PresetService
from .reaction_service import ReactionService
from .models import Artifact, Attachment, Message, Project, Thread
from .smb_service import SmbStudioService
from .store import StudioStore

try:
    from nuxiva_native import RustChatStudio
    _native_studio = RustChatStudio()
except Exception:
    _native_studio = None

try:
    from resource_actions import trimmers
    if _native_studio is not None:
        trimmers.register(
            "ai_studio_cache",
            lambda: _native_studio.cache_size_bytes(),
            lambda: _native_studio.cache_trim(512 * 1024),
        )
except Exception:
    pass

log = logging.getLogger("nuxiva.ai_studio")
TITLE_MAX = 60
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
        self.knowledge = KnowledgeService(self.store)
        self.audit = AuditService(self.store)
        self.execution = ExecutionService()
        self.dlp = DlpService()
        self.presets = PresetService(self.store)
        self.reactions = ReactionService(self.store)

    async def compare_modes(
        self,
        prompt: str,
        modes: Optional[List[str]] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        target_modes = [m for m in (modes or ["fast", "reasoning", "creative", "code"]) if m in ("fast", "reasoning", "creative", "code")]
        if not target_modes:
            target_modes = ["fast", "reasoning"]

        project = self.store.get_project(project_id) if project_id else None
        system_parts = ["Sei Nuxiva Studio AI. Rispondi alla richiesta dell'utente."]
        if project:
            system_parts.append(f"[Progetto]: {project.name}\n{project.instructions}")
        system = "\n\n".join(system_parts)

        async def _run_single(mode: str) -> Dict[str, Any]:
            start = time.perf_counter()
            raw = await self._execute_inference(prompt, system, mode)
            duration_ms = int((time.perf_counter() - start) * 1000)
            thought, clean = self._decompose_thought(raw)
            return {
                "mode": mode,
                "content": clean,
                "thought": thought,
                "duration_ms": duration_ms,
            }

        return await asyncio.gather(*[_run_single(m) for m in target_modes])

    def create_project(self, name: str, description: str = "", instructions: str = "", smb_folder: str = "") -> Project:
        now = int(time.time())
        project_id = f"proj_{now}_{uuid.uuid4().hex[:12]}"
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
        thread_id = f"th_{now}_{uuid.uuid4().hex[:12]}"
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
        return await infer(prompt, system, model_mode)

    def _prepare_thread(self, thread: Thread, content: str, history: List[Message], model_mode: Optional[str]) -> None:
        changed = False
        if model_mode in VALID_MODES and model_mode != thread.model_mode:
            thread.model_mode = model_mode
            changed = True
        if not history:
            title = " ".join(content.split())[:TITLE_MAX].strip()
            if title:
                thread.title = title
                changed = True
        if changed:
            thread.updated_at = int(time.time())
            self.store.save_thread(thread)

    async def send_message(
        self,
        thread_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        preset_id: Optional[str] = None,
        actor: str = "admin",
        model_mode: Optional[str] = None,
    ) -> Message:
        now = int(time.time())
        thread = self.store.get_thread(thread_id)
        if not thread:
            thread = self.create_thread(title=content[:30] or "Chat", model_mode=model_mode or "reasoning")
        history = self.store.list_messages(thread.id)
        self._prepare_thread(thread, content, history, model_mode)

        user_msg = Message(
            id=f"msg_u_{now}_{uuid.uuid4().hex[:6]}",
            thread_id=thread.id,
            role="user",
            content=content.strip(),
            thought="",
            artifacts=[],
            attachments=attachments or [],
            memory_recalls=[],
            created_at=now,
        )
        masked_content, dlp_matches = self.dlp.inspect_and_mask(content)
        if dlp_matches:
            self.audit.append(actor, "dlp.mask", f"thread={thread.id} rules={[d['rule'] for d in dlp_matches]}")
            content = masked_content
            user_msg.content = masked_content

        self.store.add_message(user_msg)
        self.audit.append(actor, "message.send", f"thread={thread.id} preset={preset_id or '-'} chars={len(content)}")
        self.memory.learn(content=content, source="written_chat", speaker="user")

        project = self.store.get_project(thread.project_id) if thread.project_id else None
        memory_recalls = self.memory.recall(content, limit=5)
        memory_context = self.memory.build_system_injection(content)

        cache_key = ""
        now_ms = int(time.time() * 1000)
        if _native_studio is not None and not attachments and not history:
            cache_key = _native_studio.cache_derive_key(content, thread.model_mode, thread.project_id)
            cached_raw = _native_studio.cache_get(cache_key, now_ms)
            if cached_raw:
                try:
                    cdata = json.loads(cached_raw)
                    raw_arts = json.loads(cdata.get("artifacts_json", "[]"))
                    cached_artifacts = [
                        Artifact(
                            id=a.get("id", ""),
                            identifier=a.get("identifier", ""),
                            title=a.get("title", ""),
                            kind=a.get("kind", ""),
                            language=a.get("language", ""),
                            content=a.get("content", ""),
                        )
                        for a in raw_arts
                    ]
                    cached_msg = Message(
                        id=f"msg_a_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                        thread_id=thread.id,
                        role="assistant",
                        content=cdata.get("content", ""),
                        thought=cdata.get("thought", ""),
                        artifacts=cached_artifacts,
                        attachments=[],
                        memory_recalls=memory_recalls,
                        created_at=int(time.time()),
                        cached=True,
                    )
                    self.store.add_message(cached_msg)
                    return cached_msg
                except (ValueError, TypeError, AttributeError) as exc:
                    log.warning("Risposta in cache di AI Studio non leggibile: %s", exc)

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
        if project:
            knowledge_context = self.knowledge.build_context(project.id, content)
            if knowledge_context:
                system_parts.append(f"\n{knowledge_context}")

        preset = self.presets.get(preset_id) if preset_id else None
        if preset and preset["system_prompt"].strip():
            system_parts.append(f"\n[Preset: {preset['name']}]\n{preset['system_prompt']}")

        full_system = "\n\n".join(system_parts)

        att_summary = ""
        if attachments:
            att_lines = [f"- {a.name} ({a.kind}, {a.mime_type})" for a in attachments]
            att_summary = "\n[Allegati inclusi]:\n" + "\n".join(att_lines) + "\n"

        prompt = build_prompt(content, history, att_summary)
        raw_response = await self._execute_inference(prompt, full_system, thread.model_mode)

        thought, clean_content = self._decompose_thought(raw_response)
        artifacts = ArtifactExtractor.extract(clean_content)

        assistant_msg = Message(
            id=f"msg_a_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            thread_id=thread.id,
            role="assistant",
            content=clean_content,
            thought=thought,
            artifacts=artifacts,
            attachments=[],
            memory_recalls=memory_recalls,
            created_at=int(time.time()),
            cached=False,
        )
        self.store.add_message(assistant_msg)

        if _native_studio is not None and cache_key and not history:
            art_json = json.dumps([a.to_dict() for a in artifacts])
            _native_studio.cache_put(
                cache_key,
                clean_content,
                thought,
                art_json,
                thread.model_mode,
                3600,
                now_ms,
            )

        return assistant_msg
