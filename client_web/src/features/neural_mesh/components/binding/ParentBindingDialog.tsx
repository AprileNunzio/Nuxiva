import React, { useEffect, useRef, useState } from 'react';
import { Atom, Check, Cpu, Link2, Loader2, X } from 'lucide-react';
import { reportError } from '../../../../shared/errors/errorBus';
import { bindParent } from '../../data/meshApi';
import { MeshNeuron, STREAM_KINDS, StreamKind } from '../../domain/types';
import { useMeshI18n } from '../../i18nScope';

interface ParentBindingDialogProps {
  readonly neuron: MeshNeuron;
  readonly candidates: readonly MeshNeuron[];
  readonly onClose: () => void;
  readonly onBound: (neuronId: string, parentId: string | null) => void;
}

const CORE_OPTION = '__core__';

export const ParentBindingDialog: React.FC<ParentBindingDialogProps> = ({ neuron, candidates, onClose, onBound }) => {
  const { t } = useMeshI18n();
  const [target, setTarget] = useState<string>(neuron.parentId ?? CORE_OPTION);
  const [stream, setStream] = useState<StreamKind>('audio_pcm');
  const [submitting, setSubmitting] = useState(false);
  const [failed, setFailed] = useState(false);
  const firstFocusRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    firstFocusRef.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const submit = async () => {
    const parent = target === CORE_OPTION ? null : candidates.find((c) => c.id === target) ?? null;
    setSubmitting(true);
    setFailed(false);
    try {
      await bindParent({ neuron, parent, stream });
      onBound(neuron.id, parent ? parent.id : null);
      onClose();
    } catch (cause) {
      reportError('bind_failed', cause);
      setFailed(true);
    } finally {
      setSubmitting(false);
    }
  };

  const option = (id: string, label: string, detail: string, icon: React.ReactNode, ref?: React.Ref<HTMLButtonElement>) => {
    const selected = target === id;
    return (
      <li key={id}>
        <button
          ref={ref}
          type="button"
          role="radio"
          aria-checked={selected}
          onClick={() => setTarget(id)}
          className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
            selected ? 'border-cyan-400/70 bg-cyan-400/10' : 'border-slate-800 bg-slate-900/50 hover:border-slate-600'
          }`}
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-950/80">{icon}</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-white">{label}</span>
            <span className="block truncate text-xs text-slate-400">{detail}</span>
          </span>
          {selected && <Check className="h-4 w-4 shrink-0 text-cyan-300" aria-hidden="true" />}
        </button>
      </li>
    );
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="nm-bind-title"
        onClick={(event) => event.stopPropagation()}
        className="nm-glass nm-enter flex max-h-[92vh] w-full max-w-lg flex-col gap-4 overflow-y-auto rounded-t-2xl border border-cyan-400/30 p-5 shadow-[0_0_60px_rgba(34,211,238,0.18)] sm:rounded-2xl"
      >
        <header className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link2 className="h-5 w-5 text-cyan-300" aria-hidden="true" />
            <div>
              <h2 id="nm-bind-title" className="nm-display text-lg font-bold tracking-wide text-white">
                {t('bind_title')}
              </h2>
              <p className="text-xs text-slate-400">{t('bind_subtitle', { name: neuron.name })}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('action_close')}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </header>

        <fieldset>
          <legend className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{t('bind_target_label')}</legend>
          <ul role="radiogroup" className="flex max-h-64 flex-col gap-2 overflow-y-auto pr-1">
            {option(CORE_OPTION, t('bind_core_option'), t('bind_core_detail'), <Atom className="h-4 w-4 text-cyan-200" />, firstFocusRef)}
            {candidates.map((c) =>
              option(c.id, c.name, c.ip ?? t('value_unavailable'), <Cpu className="h-4 w-4 text-cyan-300" />),
            )}
          </ul>
        </fieldset>

        <label className="flex flex-col gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{t('bind_stream_label')}</span>
          <select
            value={stream}
            onChange={(event) => {
              const next = event.target.value as StreamKind;
              if (STREAM_KINDS.includes(next)) {
                setStream(next);
              }
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 p-2.5 text-sm text-white focus:border-cyan-400 focus:outline-none"
          >
            {STREAM_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {t(`stream_${kind}`)}
              </option>
            ))}
          </select>
        </label>

        {failed && (
          <p role="alert" className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            {t('bind_error')}
          </p>
        )}

        <footer className="flex flex-col-reverse gap-2 border-t border-slate-800 pt-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t('action_cancel')}
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {t('bind_confirm')}
          </button>
        </footer>
      </div>
    </div>
  );
};
