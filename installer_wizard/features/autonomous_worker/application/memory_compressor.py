import time

from features.autonomous_worker.domain.models import CollabMessage, Mission
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.autonomous_worker.domain.sanitizer import sanitize_text

COMPRESSION_THRESHOLD = 18
KEEP_RECENT = 6

SYNTHESIS_SYSTEM_PROMPT = (
    "Sei l'Agente Sintetizzatore della Memoria di Nuxiva: analitico, conciso, orientato "
    "a non far ripetere errori al team. Analizza i messaggi della missione, aggiorna il sommario "
    "dello stato, estrai le lezioni apprese (errori superati, vincoli negativi da non ripetere) "
    "e le decisioni chiave prese dal team. Rispondi esclusivamente in formato JSON: "
    "{\n"
    '  "summary": "Sommario denso dello stato attuale e decisioni",\n'
    '  "lessons_learned": ["Regola negativa 1 per non ripetere errori", "Regola 2"],\n'
    '  "key_decisions": ["Decisione architetturale 1", "Decisione 2"]\n'
    "}"
)


class MemoryCompressor:
    def should_compress(self, mission: Mission) -> bool:
        return len(mission.collab_messages) >= COMPRESSION_THRESHOLD

    async def compress(self, mission: Mission) -> bool:
        if not self.should_compress(mission):
            return False

        messages_to_compress = mission.collab_messages[:-KEEP_RECENT]
        dialogue_text = "\n".join(
            f"[{m.sender_role or m.sender_id} -> {m.target_id}] ({m.kind}): {m.content}"
            for m in messages_to_compress
        )

        prompt = (
            f"MISSIONE: {mission.title}\n"
            f"OBIETTIVO: {mission.goal}\n"
            f"SOMMARIO PRECEDENTE: {mission.memory.summary or 'Nessuno'}\n"
            f"LEZIONI GIA NOTE: {'; '.join(mission.memory.lessons_learned) or 'Nessuna'}\n"
            f"CRONOLOGIA DA CONSOLIDARE:\n{dialogue_text}\n"
        )

        try:
            data = await runtime_manager.generate(
                prompt=prompt,
                as_json=True,
                max_tokens=1200,
                temperature=0.1,
                system=SYNTHESIS_SYSTEM_PROMPT,
                component="autonomous_worker_memory",
            )
            if not isinstance(data, dict):
                return False

            new_summary = sanitize_text(data.get("summary") or mission.memory.summary, 1200)
            raw_lessons = data.get("lessons_learned", [])
            new_lessons = [sanitize_text(l, 300) for l in raw_lessons if isinstance(l, str)]
            raw_decisions = data.get("key_decisions", [])
            new_decisions = [sanitize_text(d, 300) for d in raw_decisions if isinstance(d, str)]

            combined_lessons = list(dict.fromkeys(mission.memory.lessons_learned + new_lessons))[:40]
            combined_decisions = list(dict.fromkeys(mission.memory.key_decisions + new_decisions))[:40]

            mission.memory.summary = new_summary
            mission.memory.lessons_learned = combined_lessons
            mission.memory.key_decisions = combined_decisions
            mission.memory.last_compressed_at = time.time()
            mission.memory.compression_count += 1

            mission.collab_messages = mission.collab_messages[-KEEP_RECENT:]

            compression_notice = CollabMessage(
                id=f"msg_compress_{int(time.time())}",
                sender_id="memory_synthesizer",
                sender_role="Sintetizzatore Memoria",
                target_id="all",
                channel=f"mission:{mission.id}",
                content=(
                    f"Cronologia consolidata con successo (ciclo #{mission.memory.compression_count}). "
                    f"Preservate {len(combined_lessons)} lezioni apprese e {len(combined_decisions)} decisioni chiave."
                ),
                kind="system_memory",
                timestamp=time.time(),
            )
            mission.collab_messages.append(compression_notice)
            return True
        except Exception:
            return False


memory_compressor = MemoryCompressor()
