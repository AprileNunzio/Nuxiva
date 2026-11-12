import React, { FormEvent, useEffect, useState } from 'react';
import { FolderOpen, Loader2, Save, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { Panel } from '../../shared/components/ModuleFrame';
import { SAVE_NAME, deleteSave, listSaves, loadBoard, saveBoard } from '../data/boardApi';
import { BoardHandle } from '../hooks/useBoard';
import { fieldClass, useBoardI18n } from '../scope';

export const SavesPanel: React.FC<{ readonly handle: BoardHandle }> = ({ handle }) => {
  const { t } = useBoardI18n();
  const [saves, setSaves] = useState<readonly string[] | null>(null);
  const [name, setName] = useState('');
  const [confirm, setConfirm] = useState<{ kind: 'load' | 'delete'; name: string } | null>(null);
  const [tick, setTick] = useState(0);
  const busy = handle.busy !== null;

  useEffect(() => {
    const controller = new AbortController();
    listSaves(controller.signal)
      .then(setSaves)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_board_saves_failed', cause));
    return () => controller.abort();
  }, [tick]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const clean = name.trim();
    if (SAVE_NAME.test(clean) && (await handle.run('save', () => saveBoard(clean), 'node_board_save_failed'))) {
      setName('');
      setTick((value) => value + 1);
    }
  };

  const act = async () => {
    if (!confirm) {
      return;
    }
    const { kind, name: target } = confirm;
    const ok =
      kind === 'load'
        ? await handle.run(`load:${target}`, () => loadBoard(target), 'node_board_load_failed')
        : await handle.run(`delete:${target}`, () => deleteSave(target), 'node_board_delete_failed');
    if (ok) {
      setTick((value) => value + 1);
    }
    setConfirm(null);
  };

  return (
    <Panel title={t('saves_title')}>
      <form onSubmit={submit} className="flex gap-2">
        <input
          aria-label={t('save_name')}
          placeholder={t('save_name')}
          maxLength={50}
          value={name}
          onChange={(event) => setName(event.target.value)}
          className={`${fieldClass} min-w-0 flex-1`}
        />
        <button
          type="submit"
          disabled={busy || !SAVE_NAME.test(name.trim())}
          className="flex items-center gap-1.5 rounded-xl bg-cyan-400 px-3 py-2 text-xs font-bold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-100"
        >
          {handle.busy === 'save' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Save className="h-3.5 w-3.5" aria-hidden="true" />}
          {t('save')}
        </button>
      </form>
      {saves === null ? (
        <Loader2 className="mt-3 h-4 w-4 animate-spin text-cyan-300" aria-label={t('loading')} />
      ) : saves.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{t('saves_empty')}</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-1.5">
          {saves.map((save) => (
            <li key={save} className="flex items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-1.5">
              <span className="min-w-0 flex-1 truncate text-sm text-slate-200">{save}</span>
              <button
                type="button"
                disabled={busy}
                onClick={() => setConfirm({ kind: 'load', name: save })}
                className="flex items-center gap-1 rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-200 transition hover:border-cyan-400/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                <FolderOpen className="h-3.5 w-3.5" aria-hidden="true" />
                {t('load')}
              </button>
              <button
                type="button"
                disabled={busy}
                aria-label={t('delete')}
                onClick={() => setConfirm({ kind: 'delete', name: save })}
                className="rounded-lg p-1.5 text-slate-500 transition hover:text-rose-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {confirm && (
        <ConfirmDialog
          title={t(confirm.kind === 'load' ? 'load_title' : 'delete_title')}
          body={t(confirm.kind === 'load' ? 'load_body' : 'delete_body', { name: confirm.name })}
          confirmLabel={t(confirm.kind === 'load' ? 'load' : 'delete')}
          cancelLabel={t('cancel')}
          pending={busy}
          tone={confirm.kind === 'load' ? 'neutral' : 'danger'}
          onConfirm={() => void act()}
          onCancel={() => setConfirm(null)}
        />
      )}
    </Panel>
  );
};
