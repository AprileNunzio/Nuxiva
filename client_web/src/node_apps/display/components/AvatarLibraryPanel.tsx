import React, { FormEvent, useRef, useState } from 'react';
import { Box, Check, Loader2, Trash2, Upload } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { Panel } from '../../shared/components/ModuleFrame';
import { AVATAR_ACCEPT, AVATAR_NAME, activateAvatar, deleteAvatar, uploadAvatar } from '../data/displayApi';
import { AvatarsHandle } from '../hooks/useAvatars';
import { fieldClass, useDisplayI18n } from '../scope';

const megabytes = (bytes: number): string => (bytes / 1024 / 1024).toFixed(bytes < 1024 * 1024 ? 2 : 1);

export const AvatarLibraryPanel: React.FC<{ readonly handle: AvatarsHandle }> = ({ handle }) => {
  const { t } = useDisplayI18n();
  const { library, busy } = handle;
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [tooBig, setTooBig] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  if (!library) {
    return (
      <Panel title={t('avatars_title')}>
        <Loader2 className="h-5 w-5 animate-spin text-cyan-300" aria-label={t('loading')} />
      </Panel>
    );
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !AVATAR_NAME.test(name)) {
      return;
    }
    if (await handle.run('upload', () => uploadAvatar(name, file), 'node_avatar_upload_failed')) {
      setName('');
      setFile(null);
      if (input.current) {
        input.current.value = '';
      }
    }
  };

  const option = (key: string, label: string, detail: string, active: boolean, onPick: () => void, extra?: React.ReactNode, pickable = true) => (
    <li
      key={key}
      className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${active ? 'border-cyan-400/60 bg-cyan-400/5' : 'border-slate-800/80 bg-slate-950/40'}`}
    >
      <Box className={`h-4 w-4 shrink-0 ${active ? 'text-cyan-200' : 'text-slate-500'}`} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm text-slate-100">{label}</span>
        <span className="block truncate text-[11px] text-slate-500">{detail}</span>
      </span>
      {active ? (
        <span className="flex items-center gap-1 text-xs font-semibold text-cyan-200">
          <Check className="h-3.5 w-3.5" aria-hidden="true" />
          {t('avatar_active')}
        </span>
      ) : (
        <button
          type="button"
          disabled={busy !== null || !pickable}
          onClick={onPick}
          className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-200 transition hover:border-cyan-400/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {busy === `activate:${key}` ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : t('avatar_use')}
        </button>
      )}
      {extra}
    </li>
  );

  return (
    <Panel title={t('avatars_title')}>
      <ul className="flex flex-col gap-2">
        {option('', t('avatar_default'), t('avatar_default_hint'), library.active === '', () =>
          void handle.run('activate:', () => activateAvatar(''), 'node_avatar_activate_failed'),
        )}
        {library.avatars.map((avatar) =>
          option(
            avatar.name,
            avatar.name,
            avatar.model
              ? `${avatar.model} · ${megabytes(avatar.files.reduce((sum, f) => sum + f.size, 0))} MB`
              : t('avatar_no_model'),
            library.active === avatar.name,
            () => void handle.run(`activate:${avatar.name}`, () => activateAvatar(avatar.name), 'node_avatar_activate_failed'),
            <button
              type="button"
              aria-label={t('avatar_remove')}
              disabled={busy !== null}
              onClick={() => setRemoving(avatar.name)}
              className="rounded-lg p-1.5 text-slate-500 transition hover:text-rose-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            </button>,
            avatar.model !== null,
          ),
        )}
      </ul>
      <form onSubmit={submit} className="mt-4 grid gap-2 border-t border-slate-800/80 pt-3 sm:grid-cols-2">
        <p className="text-xs text-slate-500 sm:col-span-2">{t('upload_hint', { max: megabytes(library.maxBytes) })}</p>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('upload_name')}
          <input
            required
            maxLength={40}
            pattern="[A-Za-z0-9][A-Za-z0-9_\-]{0,39}"
            value={name}
            onChange={(event) => setName(event.target.value.replace(/[^A-Za-z0-9_-]/g, ''))}
            className={fieldClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('upload_file')}
          <input
            ref={input}
            required
            type="file"
            accept={AVATAR_ACCEPT}
            onChange={(event) => {
              const picked = event.target.files?.[0] ?? null;
              setTooBig(picked !== null && picked.size > library.maxBytes);
              setFile(picked);
            }}
            className={`${fieldClass} py-1.5 file:mr-2 file:rounded-lg file:border-0 file:bg-cyan-400/15 file:px-2 file:py-1 file:text-xs file:text-cyan-100`}
          />
        </label>
        {tooBig && (
          <p role="alert" className="text-xs text-rose-300 sm:col-span-2">
            {t('upload_too_big')}
          </p>
        )}
        <button
          type="submit"
          disabled={busy !== null || !file || tooBig || !AVATAR_NAME.test(name)}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200 sm:col-span-2"
        >
          {busy === 'upload' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Upload className="h-4 w-4" aria-hidden="true" />}
          {t('upload_submit')}
        </button>
      </form>
      {removing && (
        <ConfirmDialog
          title={t('remove_title')}
          body={t('remove_body', { name: removing })}
          confirmLabel={t('avatar_remove')}
          cancelLabel={t('cancel')}
          pending={busy === `remove:${removing}`}
          tone="danger"
          onConfirm={() => void handle.run(`remove:${removing}`, () => deleteAvatar(removing), 'node_avatar_remove_failed').then(() => setRemoving(null))}
          onCancel={() => setRemoving(null)}
        />
      )}
    </Panel>
  );
};
