import React, { useState } from 'react';
import { Bot, Compass, MessageSquare, Send, Sparkles, UserPlus } from 'lucide-react';
import type { AgentNote, LocalizedMessage } from '../types';

interface LiveRepairCoPilotProps {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly advice: readonly LocalizedMessage[];
  readonly notes: readonly AgentNote[];
  readonly sessionActive: boolean;
  readonly busy: boolean;
  readonly assignedAgents: readonly string[];
  readonly onSendChat: (message: string, agentId?: string) => Promise<void>;
  readonly onEscalateSpecialist: (
    requesterId: string,
    specialty: string,
    justification: string
  ) => Promise<void>;
}

const SPECIALIST_OPTIONS = [
  { id: 'electronics_repair_engineer', labelKey: 'agent_electronics' },
  { id: 'pcb_schematic_architect', labelKey: 'agent_schematic' },
  { id: 'embedded_firmware_coder', labelKey: 'agent_firmware' },
  { id: 'audio_acoustics_specialist', labelKey: 'agent_audio' },
] as const;

function renderLocalized(
  t: (key: string, params?: Record<string, string | number>) => string,
  msg: LocalizedMessage
): string {
  if (msg.key) {
    return t(msg.key, msg.params || {});
  }
  return msg.text || '';
}

export const LiveRepairCoPilot: React.FC<LiveRepairCoPilotProps> = ({
  t,
  advice,
  notes,
  sessionActive,
  busy,
  assignedAgents,
  onSendChat,
  onEscalateSpecialist,
}) => {
  const [selectedAgent, setSelectedAgent] = useState<string>('electronics_repair_engineer');
  const [chatText, setChatText] = useState<string>('');
  const [escalateOpen, setEscalateOpen] = useState<boolean>(false);
  const [specialty, setSpecialty] = useState<string>('');
  const [justification, setJustification] = useState<string>('');

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = chatText.trim();
    if (!trimmed || !sessionActive) return;
    setChatText('');
    await onSendChat(trimmed, selectedAgent);
  };

  const handleEscalateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!specialty.trim() || !justification.trim() || !sessionActive) return;
    await onEscalateSpecialist(selectedAgent, specialty.trim(), justification.trim());
    setSpecialty('');
    setJustification('');
    setEscalateOpen(false);
  };

  return (
    <section className="relative flex h-full w-full flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/95">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 bg-slate-900/90 px-3 py-2 text-xs">
        <div className="flex items-center gap-2 font-semibold text-cyan-300">
          <Sparkles className="h-4 w-4 text-cyan-400" aria-hidden="true" />
          <span>{t('copilot_title')}</span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {assignedAgents.filter((id) => !['chief_supervisor', 'project_director'].includes(id)).map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => setSelectedAgent(id)}
              className={`rounded-lg border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                selectedAgent === id
                  ? 'border-cyan-500/60 bg-cyan-500/20 text-cyan-200'
                  : 'border-slate-700 bg-slate-900 text-slate-400 hover:text-slate-200'
              }`}
            >
              {SPECIALIST_OPTIONS.some((spec) => spec.id === id)
                ? t(SPECIALIST_OPTIONS.find((spec) => spec.id === id)!.labelKey)
                : id.replace(/^expert_/, '').replace(/_/g, ' ')}
            </button>
          ))}
          <button
            type="button"
            disabled={!sessionActive || busy}
            onClick={() => setEscalateOpen(true)}
            className="inline-flex items-center gap-1 rounded-lg border border-amber-500/40 bg-amber-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-amber-300 hover:bg-amber-500/25 disabled:opacity-40"
          >
            <UserPlus className="h-3 w-3" aria-hidden="true" />
            {t('copilot_escalate_btn')}
          </button>
        </div>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-3 overflow-y-auto p-3 text-xs md:grid-cols-12">
        <div className="flex flex-col gap-2 rounded-xl border border-slate-800/80 bg-slate-900/50 p-2.5 md:col-span-5">
          <div className="flex items-center gap-1.5 font-semibold text-emerald-300">
            <Compass className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{t('copilot_advice_header')}</span>
          </div>
          {advice.length === 0 ? (
            <p className="text-slate-400">{t('copilot_advice_empty')}</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {advice.map((item, idx) => (
                <li
                  key={idx}
                  className="rounded-lg border border-emerald-500/25 bg-emerald-950/30 px-2.5 py-1.5 text-emerald-100"
                >
                  {renderLocalized(t, item)}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col justify-between gap-2 rounded-xl border border-slate-800/80 bg-slate-900/50 p-2.5 md:col-span-7">
          <div className="flex max-h-36 flex-col gap-1.5 overflow-y-auto pr-1">
            {notes.length === 0 ? (
              <div className="flex items-center gap-2 text-slate-400">
                <MessageSquare className="h-4 w-4 text-slate-600" aria-hidden="true" />
                <span>{t('copilot_chat_placeholder')}</span>
              </div>
            ) : (
              notes.map((note, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-2.5 py-1.5"
                >
                  <Bot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-400" aria-hidden="true" />
                  <div className="flex-1">
                    <span className="mr-1.5 font-mono text-[10px] font-semibold text-cyan-300">
                      {SPECIALIST_OPTIONS.some((spec) => spec.id === note.agent_id)
                        ? t(SPECIALIST_OPTIONS.find((spec) => spec.id === note.agent_id)!.labelKey)
                        : note.agent_id.replace(/^expert_/, '').replace(/_/g, ' ')}
                    </span>
                    <span className="text-slate-200">{renderLocalized(t, note.message)}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          <form onSubmit={handleChatSubmit} className="flex items-center gap-2 pt-1">
            <input
              type="text"
              value={chatText}
              maxLength={1200}
              disabled={!sessionActive || busy}
              onChange={(e) => setChatText(e.target.value)}
              placeholder={t('copilot_chat_placeholder')}
              className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 disabled:opacity-40"
            />
            <button
              type="submit"
              disabled={!sessionActive || busy || !chatText.trim()}
              className="inline-flex items-center gap-1 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-40"
            >
              <Send className="h-3.5 w-3.5" aria-hidden="true" />
              {t('copilot_send')}
            </button>
          </form>
        </div>
      </div>

      {escalateOpen && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <form
            onSubmit={handleEscalateSubmit}
            className="flex w-full max-w-md flex-col gap-3 rounded-xl border border-slate-700 bg-slate-900 p-4 text-xs text-slate-100 shadow-2xl"
          >
            <h3 className="text-sm font-semibold text-amber-300">{t('copilot_escalate_title')}</h3>
            <input
              type="text"
              value={specialty}
              maxLength={80}
              onChange={(e) => setSpecialty(e.target.value)}
              placeholder={t('copilot_specialty_placeholder')}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
              required
            />
            <input
              type="text"
              value={justification}
              maxLength={400}
              onChange={(e) => setJustification(e.target.value)}
              placeholder={t('copilot_justification_placeholder')}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
              required
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEscalateOpen(false)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800"
              >
                {t('popup_cancel')}
              </button>
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-amber-600 px-3 py-1.5 font-semibold text-white hover:bg-amber-500 disabled:opacity-40"
              >
                {t('copilot_confirm_escalate')}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
};
