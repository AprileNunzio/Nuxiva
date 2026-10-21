import React, { FormEvent, useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { NewPrinter, addPrinter } from '../data/printersApi';
import { fieldClass, usePrintersI18n } from '../scope';

const TYPES: readonly NewPrinter['type'][] = ['laser_2d', 'inkjet_2d', '3d', 'engraver'];
const EMPTY: NewPrinter = { name: '', type: 'laser_2d', connection: 'network', address: '', port: 9100, api_key: '' };

export const AddPrinterPanel: React.FC<{ readonly onAdded: () => void }> = ({ onAdded }) => {
  const { t } = usePrintersI18n();
  const [draft, setDraft] = useState<NewPrinter>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setFailed(false);
    try {
      await addPrinter({ ...draft, name: draft.name.trim(), address: draft.address.trim() });
      setDraft(EMPTY);
      onAdded();
    } catch (cause) {
      reportError('node_printer_add_failed', cause);
      setFailed(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title={t('add_title')}>
      <form onSubmit={submit} className="grid gap-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('add_name')}
          <input required maxLength={60} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} className={fieldClass} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('add_type')}
          <select
            value={draft.type}
            onChange={(event) => {
              const type = TYPES.find((value) => value === event.target.value) ?? 'laser_2d';
              setDraft({ ...draft, type, port: type === '3d' ? 7125 : 9100 });
            }}
            className={fieldClass}
          >
            {TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`type_${type}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('add_connection')}
          <select
            value={draft.connection}
            onChange={(event) => setDraft({ ...draft, connection: event.target.value === 'usb' ? 'usb' : 'network' })}
            className={fieldClass}
          >
            <option value="network">{t('connection_network')}</option>
            <option value="usb">{t('connection_usb')}</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t(draft.connection === 'usb' ? 'add_serial' : 'add_address')}
          <input
            required
            maxLength={200}
            value={draft.address}
            placeholder={draft.connection === 'usb' ? '/dev/ttyUSB0' : '192.168.1.50'}
            onChange={(event) => setDraft({ ...draft, address: event.target.value })}
            className={`${fieldClass} font-mono`}
          />
        </label>
        {draft.connection === 'network' && (
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t('add_port')}
            <input
              type="number"
              min={1}
              max={65535}
              value={draft.port}
              onChange={(event) => setDraft({ ...draft, port: Math.min(65535, Math.max(1, Number(event.target.value) || 1)) })}
              className={fieldClass}
            />
          </label>
        )}
        {draft.type === '3d' && (
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            {t('add_api_key')}
            <input
              type="password"
              autoComplete="off"
              maxLength={200}
              value={draft.api_key}
              onChange={(event) => setDraft({ ...draft, api_key: event.target.value })}
              className={fieldClass}
            />
          </label>
        )}
        {failed && (
          <p role="alert" className="text-xs text-rose-300 sm:col-span-2">
            {t('add_failed')}
          </p>
        )}
        <button
          type="submit"
          disabled={saving}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200 sm:col-span-2"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
          {t('add_submit')}
        </button>
      </form>
    </Panel>
  );
};
