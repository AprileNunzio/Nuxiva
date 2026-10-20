import React, { useEffect, useState } from 'react';
import { Loader2, Save } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { ORIENTATIONS, PAPERS, Printer, PrinterOptions, QUALITIES, saveOptions } from '../data/printersApi';
import { fieldClass, usePrintersI18n } from '../scope';

type NumberKey = 'copies' | 'laser_power' | 'laser_feed' | 'nozzle_temp' | 'bed_temp';
const LIMITS: Readonly<Record<NumberKey, readonly [number, number]>> = {
  copies: [1, 99],
  laser_power: [0, 1000],
  laser_feed: [10, 10000],
  nozzle_temp: [0, 300],
  bed_temp: [0, 120],
};

export const PrinterOptionsPanel: React.FC<{ readonly printer: Printer; readonly onSaved: () => void }> = ({ printer, onSaved }) => {
  const { t } = usePrintersI18n();
  const [draft, setDraft] = useState<PrinterOptions>(printer.options);
  const [isDefault, setIsDefault] = useState(printer.isDefault);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(printer.options);
    setIsDefault(printer.isDefault);
  }, [printer]);

  const numberField = (key: NumberKey) => (
    <label key={key} className="flex flex-col gap-1 text-xs text-slate-400">
      {t(`option_${key}`)}
      <input
        type="number"
        min={LIMITS[key][0]}
        max={LIMITS[key][1]}
        value={draft[key]}
        onChange={(event) =>
          setDraft({ ...draft, [key]: Math.min(LIMITS[key][1], Math.max(LIMITS[key][0], Number(event.target.value) || LIMITS[key][0])) })
        }
        className={fieldClass}
      />
    </label>
  );

  const choice = (key: 'paper' | 'orientation' | 'quality', values: readonly string[]) => (
    <label key={key} className="flex flex-col gap-1 text-xs text-slate-400">
      {t(`option_${key}`)}
      <select value={draft[key]} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} className={fieldClass}>
        {values.map((value) => (
          <option key={value} value={value}>
            {key === 'paper' ? value : t(`value_${value}`)}
          </option>
        ))}
      </select>
    </label>
  );

  const save = async () => {
    setSaving(true);
    try {
      await saveOptions(printer.id, draft, isDefault);
      onSaved();
    } catch (cause) {
      reportError('node_printer_options_failed', cause);
    } finally {
      setSaving(false);
    }
  };

  const paper = printer.type === 'laser_2d' || printer.type === 'inkjet_2d';
  return (
    <Panel title={t('options_title', { name: printer.type === 'virtual_pdf' ? t('virtual_pdf_name') : printer.name })}>
      <div className="grid gap-2 sm:grid-cols-2">
        {paper && [choice('paper', PAPERS), choice('orientation', ORIENTATIONS), choice('quality', QUALITIES), numberField('copies')]}
        {printer.type === 'engraver' && [numberField('laser_power'), numberField('laser_feed')]}
        {printer.type === '3d' && [numberField('nozzle_temp'), numberField('bed_temp')]}
      </div>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {paper &&
          (['color', 'duplex'] as const).map((key) => (
            <label key={key} className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-100">
              {t(`option_${key}`)}
              <input type="checkbox" role="switch" checked={draft[key]} onChange={(event) => setDraft({ ...draft, [key]: event.target.checked })} className="h-5 w-9 accent-cyan-400" />
            </label>
          ))}
        <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-100">
          {t('option_default')}
          <input type="checkbox" role="switch" checked={isDefault} onChange={(event) => setIsDefault(event.target.checked)} className="h-5 w-9 accent-cyan-400" />
        </label>
      </div>
      <button
        type="button"
        onClick={save}
        disabled={saving}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
        {t('options_save')}
      </button>
    </Panel>
  );
};
