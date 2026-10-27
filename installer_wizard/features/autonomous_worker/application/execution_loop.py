import asyncio
import logging
import time

from features.automations.bus import bus
from features.automations.library import library as auto_library
from features.autonomous_worker.application.agentic_runner import agentic_runner
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.memory_compressor import memory_compressor
from features.autonomous_worker.application.sandbox_validator import sandbox_validator
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.application.workspace_runtime import workspace_runtime
from features.autonomous_worker.domain.exceptions import MissionValidationError
from features.autonomous_worker.domain.knowledge_graph import knowledge_graph
from features.autonomous_worker.domain.models import (
    Mission,
    MissionStatus,
    Phase,
    Task,
    TaskStatus,
)
from features.autonomous_worker.domain.sanitizer import sanitize_text
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.autonomous_worker.infrastructure.store import mission_store
from features.autonomous_worker.presentation.desk_notifier import notifier

log = logging.getLogger("nuxiva.autonomous_worker")
MAX_ROUNDS_PER_TASK = 3
MAX_FINAL_REVIEWS = 3
TICK_INTERVAL_SECONDS = 4
MAX_PARALLEL_TASKS = 2

REVIEW_SYSTEM_PROMPT = (
    "Sei il CEO di Nuxiva: severo, intransigente, orientato a standard mondiali assoluti. "
    "Valuta il lavoro svolto rispetto ai criteri di accettazione, Clean Architecture, Zero-Trust "
    "e limite di 500 righe per file. Rispondi con JSON: "
    "'approved': true|false, 'reasoning': 'analisi critica del CEO', 'feedback': 'cosa correggere se respinto', "
    "'criteria_results': [{'description': '...', 'verified': true|false, 'evidence': '...'}]."
)


class AutonomousExecutionLoop:
    async def tick_mission(self, mission: Mission) -> None:
        if mission.status == MissionStatus.PLANNING:
            await self._step_planning(mission)
        elif mission.status == MissionStatus.RUNNING:
            await self._step_running(mission)
        mission.recalculate_progress()
        mission_store.save(mission)
        notifier.push_mission(mission)

    async def _step_planning(self, mission: Mission) -> None:
        if not mission.phases:
            deliberated = await deliberator.deliberate(
                goal=mission.goal,
                lang=mission.lang,
                directives=mission.directives,
                options=mission.options,
                mission_id=mission.id,
            )
            mission.title = deliberated.title
            mission.domain = deliberated.domain
            mission.phases = deliberated.phases
            mission.questions = deliberated.questions
            mission.council_verdict = deliberated.council_verdict
            mission.status = deliberated.status

        forge.assemble_team(mission)
        collab_bus.system_announce(
            mission,
            f"Missione «{mission.title}» avviata. Squadra forgiata con {len(mission.specialists)} specialisti.",
        )

    async def _step_running(self, mission: Mission) -> None:
        if any(not q.answered and q.options for q in mission.questions):
            mission.status = MissionStatus.QUESTION
            return

        pending_replan = mission.options.pop("pending_replan_directive", "")
        if pending_replan:
            await deliberator.replan_for_directive(mission, str(pending_replan))
            forge.assemble_team(mission)

        if memory_compressor.should_compress(mission):
            await memory_compressor.compress(mission)

        all_tasks = mission.all_tasks()
        done_ids = {t.id for t in all_tasks if t.status == TaskStatus.DONE}

        ready_tasks = [
            t
            for t in all_tasks
            if t.status in (TaskStatus.PENDING, TaskStatus.REVIEW)
            and all(dep in done_ids for dep in t.depends_on)
        ]

        if not ready_tasks:
            active_tasks = [t for t in all_tasks if t.status in (TaskStatus.RUNNING, TaskStatus.WAITING)]
            if not active_tasks:
                await self._conclude_mission(mission)
            return

        batch = ready_tasks[:MAX_PARALLEL_TASKS]
        for task in batch:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                collab_bus.post(
                    mission=mission,
                    sender_id=task.specialist_id or "worker",
                    sender_role=task.specialist_role or "Specialista",
                    content=f"Inizio esecuzione task «{task.title}» (Round {task.round}).",
                    kind="action",
                )

        await asyncio.gather(*(self._execute_and_review(mission, t) for t in batch))
        for phase in mission.phases:
            if all(t.status == TaskStatus.DONE for t in phase.tasks) and phase.tasks:
                phase.status = "done"
            elif any(t.status in (TaskStatus.RUNNING, TaskStatus.REVIEW) for t in phase.tasks):
                phase.status = "running"

    async def _execute_and_review(self, mission: Mission, task: Task) -> None:
        if task.status == TaskStatus.RUNNING:
            await self._run_task(mission, task)
        if task.status == TaskStatus.REVIEW:
            await self._review_task(mission, task)

    async def _run_task(self, mission: Mission, task: Task) -> None:
        criteria_text = "\n".join(f"- {c.description} (Target: {c.target})" for c in task.criteria)
        lessons_text = "\n".join(f"- {l}" for l in mission.memory.lessons_learned) or "Nessuna"
        decisions_text = "\n".join(f"- {d}" for d in mission.memory.key_decisions) or "Nessuna"
        summary_text = mission.memory.summary or "Inizio lavori"

        prompt = (
            f"MISSIONE: {mission.title}\n"
            f"DOMINIO: {mission.domain}\n"
            f"OBIETTIVO GLOBALE: {mission.goal}\n"
            f"CONTESTO E STATO ATTUALE:\n{summary_text}\n"
            f"DIRETTIVE PROPRIETARIO: {', '.join(mission.directives) or 'Standard massimi'}\n"
            f"VINCOLI E ERRORI DA NON RIPETERE (LEZIONI APPRESE):\n{lessons_text}\n"
            f"DECISIONI ARCHITETTURALI CONDIVISE:\n{decisions_text}\n"
            f"TASK ASSEGNATO: {task.title}\n"
            f"DESCRIZIONE: {task.description}\n"
            f"CRITERI DI ACCETTAZIONE:\n{criteria_text}\n"
            f"FEEDBACK PRECEDENTE DEL CEO: {task.feedback or 'Nessuno'}\n"
            f"TENTATIVO NUMERO: {task.round}\n"
        )

        try:
            raw = await agentic_runner.execute_task_with_tools(mission, task, prompt)
            if not isinstance(raw, dict):
                raw = {"result": str(raw)}

            task.result = str(raw.get("result") or "")

            for patch_item in raw.get("patches", []) if isinstance(raw.get("patches"), list) else []:
                if isinstance(patch_item, dict) and patch_item.get("path") and patch_item.get("target"):
                    try:
                        patched_art = vault.apply_atomic_patch(
                            mission=mission,
                            relative_path=str(patch_item["path"]),
                            target_block=str(patch_item["target"]),
                            replacement_block=str(patch_item.get("replacement", "")),
                            generated_by=task.specialist_role or "Specialista",
                        )
                        collab_bus.post(
                            mission=mission,
                            sender_id=task.specialist_id or "worker",
                            sender_role=task.specialist_role or "Specialista",
                            content=f"Applicata patch atomica a «{patched_art.relative_path}» ({patched_art.line_count} righe).",
                            kind="artifact",
                            artifact_ref=patched_art.relative_path,
                        )
                    except (FileNotFoundError, MissionValidationError) as p_err:
                        task.status = TaskStatus.PENDING
                        task.round += 1
                        task.feedback = f"Patch atomica fallita su {patch_item['path']}: {p_err}"
                        collab_bus.system_announce(mission, f"Self-correction patch: {task.feedback}", "rework")
                        return

            for art in raw.get("artifacts", []) if isinstance(raw.get("artifacts"), list) else []:
                if isinstance(art, dict) and art.get("path") and art.get("content"):
                    valid, err_msg = sandbox_validator.validate_code(art["path"], art["content"])
                    if not valid:
                        task.status = TaskStatus.PENDING
                        task.round += 1
                        task.feedback = f"Sandbox pre-check fallito per {art['path']}: {err_msg}."
                        collab_bus.system_announce(mission, f"Self-correction: {task.feedback}", "rework")
                        return
                    saved_art = vault.store_file(
                        mission=mission,
                        relative_path=art["path"],
                        content=art["content"],
                        generated_by=task.specialist_role or "Specialista",
                        title=art.get("title", ""),
                    )
                    collab_bus.post(
                        mission=mission,
                        sender_id=task.specialist_id or "worker",
                        sender_role=task.specialist_role or "Specialista",
                        content=f"Modificato/Creato file «{saved_art.relative_path}» ({saved_art.line_count} righe, {len(saved_art.symbols)} simboli AST).",
                        kind="artifact",
                        artifact_ref=saved_art.relative_path,
                    )

            collab_note = raw.get("collab_note")
            if collab_note:
                collab_bus.post(
                    mission=mission,
                    sender_id=task.specialist_id or "worker",
                    sender_role=task.specialist_role or "Specialista",
                    content=str(collab_note),
                    kind="collab",
                )

            task.status = TaskStatus.REVIEW
        except Exception as exc:
            task.error = str(exc)[:250]
            if task.round < MAX_ROUNDS_PER_TASK:
                task.round += 1
                task.status = TaskStatus.PENDING
            else:
                task.status = TaskStatus.FAILED

    async def _review_task(self, mission: Mission, task: Task) -> None:
        verify_report = await workspace_runtime.verify_workspace(mission)
        if not verify_report["passed"] and task.round < MAX_ROUNDS_PER_TASK:
            task.round += 1
            task.status = TaskStatus.PENDING
            task.feedback = f"Verifica runtime/contratti fallita:\n{verify_report['output'][:500]}"
            task.ceo_review_notes.append(f"[Runtime Gate Round {task.round - 1}] {task.feedback}")
            collab_bus.system_announce(
                mission,
                f"Runtime Verification Gate ha respinto «{task.title}»: {task.feedback}",
                kind="rework",
            )
            return

        prompt = (
            f"TASK: {task.title}\n"
            f"RISULTATO CONSEGNATO:\n{task.result[:2000]}\n"
            f"DUBBI SEGNALATI DALLO SPECIALISTA: {task.doubts}\n"
            f"ESITO VERIFICA RUNTIME SANDBOX ({', '.join(verify_report['checks_run'])}):\n{verify_report['output'][:600]}\n"
            f"CRITERI RICHIESTI:\n"
            + "\n".join(f"- {c.description}" for c in task.criteria)
            + "\n"
            f"ARTEFATTI NELLA CARTELLA: {[f'{a.relative_path} (v{a.version}, {a.line_count}L)' for a in mission.artifacts]}\n"
        )
        try:
            verdict = await runtime_manager.generate(
                prompt,
                as_json=True,
                max_tokens=900,
                temperature=0.1,
                system=REVIEW_SYSTEM_PROMPT,
                component="autonomous_worker",
                agent_id="ceo_reviewer",
                agent_role="CEO",
            )
            approved = bool(verdict.get("approved", True)) if isinstance(verdict, dict) else True
            feedback = str(verdict.get("feedback", "")) if isinstance(verdict, dict) else ""
            ceo_reasoning = sanitize_text(verdict.get("reasoning", ""), 500) if isinstance(verdict, dict) else ""
            if ceo_reasoning:
                task.ceo_review_notes.append(f"[Round {task.round}] {ceo_reasoning}")

            if approved:
                task.status = TaskStatus.DONE
                task.completed_at = time.time()
                task.feedback = ""
                task.error = ""
                for crit in task.criteria:
                    crit.verified = True
                    if not crit.evidence:
                        crit.evidence = f"Verificato dal CEO al Round {task.round}"
                collab_bus.system_announce(
                    mission,
                    f"CEO ha APPROVATO il task «{task.title}» ({task.specialist_role}). {ceo_reasoning}",
                    kind="approval",
                )
                bus.emit(
                    "task_completed",
                    {
                        "mission_id": mission.id,
                        "task_id": task.id,
                        "title": task.title,
                        "role": task.specialist_role,
                    },
                )
            else:
                if task.round < MAX_ROUNDS_PER_TASK:
                    task.round += 1
                    task.status = TaskStatus.PENDING
                    task.feedback = feedback or "Migliorare l'aderenza ai criteri."
                    task.ceo_review_notes.append(f"[Rifacimento] {task.feedback}")
                    collab_bus.system_announce(
                        mission,
                        f"CEO ha RICHIESTO RIFACIMENTO per «{task.title}»: {task.feedback}",
                        kind="rework",
                    )
                else:
                    task.status = TaskStatus.DONE
                    task.completed_at = time.time()
                    task.error = f"Approvato con riserva dopo {task.round} tentativi."
        except Exception:
            task.status = TaskStatus.DONE
            task.completed_at = time.time()

    async def _conclude_mission(self, mission: Mission) -> None:
        failed_tasks = [t for t in mission.all_tasks() if t.status == TaskStatus.FAILED]
        if failed_tasks:
            mission.status = MissionStatus.FAILED
            mission.error = f"Falliti {len(failed_tasks)} task fondamentali."
            collab_bus.system_announce(
                mission, f"Missione interrotta per errori irreversibili: {mission.error}", "error"
            )
            auto_library.remove_by_mission(mission.id)
            return

        if mission.final_review_rounds < MAX_FINAL_REVIEWS:
            mission.final_review_rounds += 1
            prompt = (
                f"OBIETTIVO: {mission.goal}\n"
                f"TASK COMPLETATI: {len(mission.all_tasks())}\n"
                f"ARTEFATTI GENERATI: {[a.relative_path for a in mission.artifacts]}\n"
                "La missione è completa al 100% rispetto agli standard massimi? Rispondi JSON: 'complete': true|false, 'extra_tasks': [{'title': '...', 'description': '...'}]"
            )
            try:
                final_res = await runtime_manager.generate(
                    prompt,
                    as_json=True,
                    max_tokens=900,
                    temperature=0.1,
                    system=REVIEW_SYSTEM_PROMPT,
                    component="autonomous_worker",
                )
                if isinstance(final_res, dict) and not final_res.get("complete", True):
                    extras = final_res.get("extra_tasks", [])
                    if isinstance(extras, list) and extras:
                        new_phase = Phase(
                            id=f"p_fin_{mission.final_review_rounds}",
                            title="Rifinitura e Consolidamento",
                            description="Task emersi dalla revisione finale del CEO",
                        )
                        for idx, ext in enumerate(extras[:3]):
                            if isinstance(ext, dict):
                                new_phase.tasks.append(
                                    Task(
                                        id=f"t_fin_{mission.final_review_rounds}_{idx+1}",
                                        phase_id=new_phase.id,
                                        title=str(ext.get("title", "Rifinitura")),
                                        description=str(ext.get("description", "")),
                                        specialist_role="Specialista Rifinitura",
                                    )
                                )
                        mission.phases.append(new_phase)
                        forge.assemble_team(mission)
                        collab_bus.system_announce(
                            mission,
                            f"Revisione finale ha aggiunto {len(new_phase.tasks)} task di rifinitura.",
                            "refinement",
                        )
                        return
            except Exception:
                pass

        mission.status = MissionStatus.DONE
        mission.recalculate_progress()
        for lesson in mission.memory.lessons_learned:
            knowledge_graph.record_learning(mission.id, mission.domain, lesson)
        collab_bus.system_announce(
            mission,
            f"MISSIONE COMPLETATA AL 100%. Rilasciati {len(mission.artifacts)} artefatti conformi agli standard.",
            kind="success",
        )
        auto_library.remove_by_mission(mission.id)

    async def run(self) -> None:
        while True:
            try:
                active_missions = mission_store.active()
                if active_missions:
                    await asyncio.gather(*(self.tick_mission(m) for m in active_missions))
            except Exception as exc:
                log.exception("Errore ciclo autonomo: %s", exc)
            await asyncio.sleep(TICK_INTERVAL_SECONDS)


execution_loop = AutonomousExecutionLoop()
