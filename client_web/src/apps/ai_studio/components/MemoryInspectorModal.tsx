import React, { useState, useEffect } from 'react';
import { useStudioI18n } from '../scope';
import type { MemoryFact } from '../types';
import { fetchMemoryFacts, learnMemory } from '../api';

interface MemoryInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MemoryInspectorModal: React.FC<MemoryInspectorModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useStudioI18n();
  const [query, setQuery] = useState('');
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [loading, setLoading] = useState(false);
  const [newFact, setNewFact] = useState('');
  const [learning, setLearning] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetchMemoryFacts(query)
      .then(setFacts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isOpen, query]);

  if (!isOpen) return null;

  const handleLearn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFact.trim() || learning) return;
    setLearning(true);
    try {
      const added = await learnMemory({
        content: newFact.trim(),
        source: 'written_chat',
        speaker: 'user',
        tags: ['manual_memory'],
      });
      setFacts((prev) => [added, ...prev]);
      setNewFact('');
    } finally {
      setLearning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-purple-400">🧠</span>
            <h2 className="text-base font-semibold text-slate-100">
              {t('memory_hud')}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors p-1"
            aria-label={t('close')}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleLearn} className="flex gap-2">
          <input
            type="text"
            value={newFact}
            onChange={(e) => setNewFact(e.target.value)}
            placeholder={t('learn_placeholder')}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500"
          />
          <button
            type="submit"
            disabled={!newFact.trim() || learning}
            className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors disabled:opacity-40"
          >
            {learning ? '...' : t('learn_btn')}
          </button>
        </form>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('memory_search')}
          className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-700"
        />

        <div className="h-72 overflow-y-auto bg-slate-950/60 rounded-xl border border-slate-800 p-2 flex flex-col gap-2">
          {loading ? (
            <div className="flex items-center justify-center h-full text-xs text-slate-500">
              ...
            </div>
          ) : facts.length === 0 ? (
            <div className="flex items-center justify-center h-full text-xs text-slate-500">
              {t('recalled_memories')}
            </div>
          ) : (
            facts.map((fact) => (
              <div
                key={fact.id}
                className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col gap-1 text-xs"
              >
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <span>{fact.source === 'voice_speech' ? '🎙️' : '💬'}</span>
                    <span className="font-semibold text-purple-400 uppercase">
                      {fact.source === 'voice_speech' ? t('voice_memory') : t('chat_memory')}
                    </span>
                    {fact.speaker && <span>({fact.speaker})</span>}
                  </span>
                  <span>{new Date(fact.timestamp * 1000).toLocaleString()}</span>
                </div>
                <p className="text-slate-200 leading-relaxed font-sans">{fact.content}</p>
              </div>
            ))
          )}
        </div>

        <div className="flex justify-end pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            {t('close')}
          </button>
        </div>
      </div>
    </div>
  );
};
