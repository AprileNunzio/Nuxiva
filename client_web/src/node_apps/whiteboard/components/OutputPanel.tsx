import React, { FormEvent, useEffect, useState } from 'react';
import { FileDown, Loader2, MessageSquareText, Printer } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { BoardPrinter, PDF_URL, askBoard, listBoardPrinters, printBoard } from '../data/boardApi';
import { BoardHandle } from '../hooks/useBoard';
import { fieldClass, useBoardI18n } from '../scope';

export const OutputPanel: React.FC<{ readonly handle: BoardHandle }> = ({ handle }) => {
  const { t } = useBoardI18n();
  const [printers, setPrinters] = useState<readonly BoardPrinter[]>([]);
  const [printer, setPrinter] = useState('');
  const [sent, setSent] = useState(false);
  const [question, setQuestion] = useState('');
  const busy = handle.busy !== null;

  useEffect(() => {
    const controller = new AbortController();
    listBoardPrinters(controller.signal)
      .then(({ printers: list, fallback }) => {
        setPrinters(list);
        setPrinter(fallback);
      })
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_board_printers_failed', cause));
    return () => controller.abort();
  }, []);

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    const clean = question.trim();
    if (clean && (await handle.run('ask', () => askBoard(clean), 'node_board_ask_failed'))) {
      setQuestion('');
    }
  };

  return (
    <Panel title={t('output_title')}>
      <form onSubmit={ask} className="flex flex-col gap-2">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('ask_label')}
          <textarea rows={2} maxLength={500} value={question} onChange={(event) => setQuestion(event.target.value)} className={`${fieldClass} resize-none`} />
        </label>
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
        >
          {handle.busy === 'ask' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <MessageSquareText className="h-4 w-4" aria-hidden="true" />}
          {t('ask_submit')}
        </button>
      </form>
      <div className="mt-4 flex flex-col gap-2 border-t border-slate-800/80 pt-3">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('printer')}
          <select value={printer} onChange={(event) => setPrinter(event.target.value)} className={fieldClass} disabled={printers.length === 0}>
            {printers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.type === 'virtual_pdf' ? t('printer_pdf') : p.name}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={busy || !printer}
            onClick={() => void handle.run('print', () => printBoard(printer), 'node_board_print_failed').then(setSent)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {handle.busy === 'print' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Printer className="h-4 w-4" aria-hidden="true" />}
            {t('print')}
          </button>
          <a
            href={PDF_URL}
            download
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-400/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {t('pdf')}
          </a>
        </div>
        {sent && (
          <p role="status" className="text-xs text-emerald-300">
            {t('print_sent')}
          </p>
        )}
      </div>
    </Panel>
  );
};
