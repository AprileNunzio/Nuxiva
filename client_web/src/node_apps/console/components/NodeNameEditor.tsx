import React, { FormEvent, useEffect, useState } from 'react';
import { Check, Loader2, Pencil, X } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { renameNode } from '../data/nodeConsoleApi';
import { CONSOLE_SCOPE } from '../scope';

const MAX_NAME = 64;

interface NodeNameEditorProps {
  readonly nodeId: string;
  readonly name: string;
  readonly onRenamed: (name: string) => void;
}

export const NodeNameEditor: React.FC<NodeNameEditorProps> = ({ nodeId, name, onRenamed }) => {
  const { t } = useScopedI18n(CONSOLE_SCOPE);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!editing) {
      setDraft(name);
    }
  }, [name, editing]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || trimmed === name) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setFailed(false);
    try {
      onRenamed(await renameNode(nodeId, trimmed));
      setEditing(false);
    } catch (cause) {
      reportError('node_rename_failed', cause);
      setFailed(true);
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <div className="flex min-w-0 items-center gap-2">
        <h1 className="truncate font-['Rajdhani'] text-2xl font-bold tracking-wide text-white sm:text-3xl">{name}</h1>
        <button
          type="button"
          onClick={() => setEditing(true)}
          aria-label={t('rename')}
          className="shrink-0 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-cyan-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <Pencil className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex min-w-0 flex-col gap-1">
      <div className="flex items-center gap-2">
        <input
          autoFocus
          value={draft}
          maxLength={MAX_NAME}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => event.key === 'Escape' && setEditing(false)}
          aria-label={t('rename_label')}
          className="min-w-0 flex-1 rounded-xl border border-cyan-400/50 bg-slate-950/80 px-3 py-1.5 font-['Rajdhani'] text-xl font-bold text-white focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
        />
        <button
          type="submit"
          disabled={saving}
          aria-label={t('rename_save')}
          className="rounded-lg bg-cyan-400 p-2 text-slate-950 transition hover:bg-cyan-300 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-100"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Check className="h-4 w-4" aria-hidden="true" />}
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          aria-label={t('rename_cancel')}
          className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      {failed && (
        <p role="alert" className="text-xs text-rose-300">
          {t('rename_error')}
        </p>
      )}
    </form>
  );
};
