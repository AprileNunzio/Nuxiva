import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useStudioI18n } from '../scope';
import * as api from '../api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  projectId: string | null;
  projectName?: string;
}

const MAX_FILE_BYTES = 2_000_000;
const TEXT_EXT = /\.(txt|md|markdown|csv|json|ya?ml|log|py|js|ts|tsx|rs|c|h|cpp|html|css|ini|conf|sh)$/i;

export const KnowledgeModal: React.FC<Props> = ({ isOpen, onClose, projectId, projectName }) => {
  const { t } = useStudioI18n();
  const [docs, setDocs] = useState<api.KnowledgeDoc[]>([]);
  const [name, setName] = useState('');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      setDocs(await api.fetchKnowledge(projectId));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [projectId]);

  useEffect(() => {
    if (isOpen) {
      setError('');
      void load();
    }
  }, [isOpen, load]);

  if (!isOpen) return null;

  const add = async (docName: string, content: string) => {
    if (!projectId || !docName.trim() || !content.trim()) return;
    setBusy(true);
    setError('');
    try {
      await api.addKnowledge(projectId, docName.trim(), content);
      setName('');
      setText('');
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onFiles = async (files: FileList | null) => {
    if (!files) return;
    for (const f of Array.from(files)) {
      if (f.size > MAX_FILE_BYTES || !(f.type.startsWith('text/') || TEXT_EXT.test(f.name))) {
        setError(`${f.name}: ${t('kb_unsupported')}`);
        continue;
      }
      await add(f.name, await f.text());
    }
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose} role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        className="w-[min(40rem,94vw)] max-h-[85vh] flex flex-col rounded-2xl border border-white/10 bg-slate-900/90 backdrop-blur-xl shadow-[0_0_60px_-15px_rgba(0,240,255,0.35)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="text-sm font-semibold text-slate-100">
            📚 {t('kb_title')}
            {projectName ? <span className="text-slate-400 font-normal"> · {projectName}</span> : null}
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-100" aria-label={t('close')}>
            ✕
          </button>
        </div>

        {!projectId ? (
          <p className="p-6 text-sm text-slate-400">{t('kb_need_project')}</p>
        ) : (
          <div className="p-4 flex flex-col gap-3 overflow-y-auto">
            <p className="text-xs text-slate-400">{t('kb_desc')}</p>

            <ul className="flex flex-col gap-1.5">
              {docs.length === 0 && <li className="text-xs text-slate-500">{t('kb_empty')}</li>}
              {docs.map((d) => (
                <li key={d.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2 text-xs">
                  <span className="truncate text-slate-200">{d.name}</span>
                  <span className="flex items-center gap-3 text-slate-500 shrink-0">
                    {d.chunks} chunk
                    <button
                      type="button"
                      className="hover:text-red-400"
                      onClick={async () => {
                        if (!projectId) return;
                        await api.deleteKnowledge(projectId, d.id).catch((e) => setError((e as Error).message));
                        void load();
                      }}
                    >
                      🗑
                    </button>
                  </span>
                </li>
              ))}
            </ul>

            <div className="flex flex-col gap-2 rounded-xl border border-white/10 p-3">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('kb_name')}
                className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500"
              />
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={5}
                placeholder={t('kb_paste')}
                className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500 resize-y"
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={busy || !name.trim() || !text.trim()}
                  onClick={() => void add(name, text)}
                  className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 text-xs font-medium text-white disabled:opacity-40"
                >
                  {t('kb_add')}
                </button>
                <input ref={fileRef} type="file" multiple className="hidden" onChange={(e) => void onFiles(e.target.files)} />
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => fileRef.current?.click()}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 hover:bg-slate-700"
                >
                  {t('kb_upload')}
                </button>
              </div>
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
};
