import React, { useEffect, useState } from 'react';
import { Box, FileDown, Flame, Loader2, Printer as PrinterIcon, Star, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Printer, ProbeState, printTestPage, probePrinter, removePrinter } from '../data/printersApi';
import { usePrintersI18n } from '../scope';

const ICONS = { laser_2d: PrinterIcon, inkjet_2d: PrinterIcon, '3d': Box, engraver: Flame, virtual_pdf: FileDown } as const;
const STATE_TONE: Readonly<Record<ProbeState, string>> = {
  ready: 'border-emerald-400/40 text-emerald-300',
  busy: 'border-amber-400/40 text-amber-200',
  offline: 'border-rose-400/40 text-rose-300',
  unknown: 'border-slate-600 text-slate-400',
};

interface PrinterCardProps {
  readonly printer: Printer;
  readonly selected: boolean;
  readonly onSelect: () => void;
  readonly onChanged: () => void;
}

export const PrinterCard: React.FC<PrinterCardProps> = ({ printer, selected, onSelect, onChanged }) => {
  const { t } = usePrintersI18n();
  const [state, setState] = useState<ProbeState | null>(null);
  const [testing, setTesting] = useState(false);
  const [feedback, setFeedback] = useState<'ok' | 'failed' | null>(null);
  const Icon = ICONS[printer.type];
  const testable = printer.type === 'laser_2d' || printer.type === 'inkjet_2d' || printer.type === 'virtual_pdf';

  useEffect(() => {
    let active = true;
    probePrinter(printer.id)
      .then((value) => active && setState(value))
      .catch(() => active && setState('unknown'));
    return () => {
      active = false;
    };
  }, [printer.id]);

  const test = async () => {
    setTesting(true);
    setFeedback(null);
    try {
      await printTestPage(printer.id);
      setFeedback('ok');
    } catch (cause) {
      reportError('node_printer_test_failed', cause);
      setFeedback('failed');
    } finally {
      setTesting(false);
    }
  };

  const remove = async () => {
    try {
      await removePrinter(printer.id);
      onChanged();
    } catch (cause) {
      reportError('node_printer_remove_failed', cause);
    }
  };

  return (
    <li
      className={`rounded-2xl border p-3 transition ${selected ? 'border-cyan-400/60 bg-cyan-400/5' : 'border-slate-800/80 bg-slate-950/40'}`}
    >
      <button type="button" onClick={onSelect} className="flex w-full items-start gap-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-700 bg-slate-900">
          <Icon className="h-5 w-5 text-cyan-200" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-100">
            <span className="truncate">{printer.type === 'virtual_pdf' ? t('virtual_pdf_name') : printer.name}</span>
            {printer.isDefault && <Star className="h-3.5 w-3.5 shrink-0 fill-amber-300 text-amber-300" aria-label={t('default_badge')} />}
          </span>
          <span className="block truncate text-[11px] text-slate-500">
            {[t(`type_${printer.type}`), t(`connection_${printer.connection}`), printer.address].filter(Boolean).join(' · ')}
          </span>
        </span>
        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${STATE_TONE[state ?? 'unknown']}`}>
          {state ? t(`state_${state}`) : <Loader2 className="h-3 w-3 animate-spin" aria-label={t('probing')} />}
        </span>
      </button>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {testable && (
          <button
            type="button"
            onClick={test}
            disabled={testing}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-200 transition hover:border-cyan-400/60 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {testing && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
            {t('test_page')}
          </button>
        )}
        {printer.custom && (
          <button
            type="button"
            onClick={() => void remove()}
            aria-label={t('remove')}
            className="ml-auto rounded-lg p-1.5 text-slate-500 transition hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
        {feedback && (
          <span role="status" className={`text-xs ${feedback === 'ok' ? 'text-emerald-300' : 'text-rose-300'}`}>
            {t(feedback === 'ok' ? 'test_sent' : 'test_failed')}
          </span>
        )}
      </div>
    </li>
  );
};
