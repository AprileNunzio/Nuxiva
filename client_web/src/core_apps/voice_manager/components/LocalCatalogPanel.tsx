import React, { useMemo, useState } from 'react';
import { Btn, Empty, Field, List, Panel, Stat, StatRow, inputClass } from '../../shared/kit';
import { OrderList } from './OrderList';
import { VoiceRow } from './VoiceRow';
import { VoiceItem, VoiceOverview } from '../types';

const PAGE = 40;
const ENGINES = ['', 'kokoro', 'piper', 'online', 'elevenlabs'] as const;

interface LocalCatalogPanelProps {
  overview: VoiceOverview;
  installed: number;
  busy: boolean;
  playing: string;
  t: (key: string, options?: Record<string, unknown>) => string;
  onSaveOrder: (next: string[]) => void;
  onPlay: (id: string) => void;
  onDownload: (id: string) => void;
  onRemove: (id: string) => void;
  onPrefer: (voice: VoiceItem) => void;
}

export const LocalCatalogPanel: React.FC<LocalCatalogPanelProps> = ({
  overview,
  installed,
  busy,
  playing,
  t,
  onSaveOrder,
  onPlay,
  onDownload,
  onRemove,
  onPrefer,
}) => {
  const [lang, setLang] = useState('');
  const [engine, setEngine] = useState('');
  const [query, setQuery] = useState('');
  const [installedOnly, setInstalledOnly] = useState(false);
  const [limit, setLimit] = useState(PAGE);

  const ids = useMemo(() => new Set(overview.order.map((v) => v.id)), [overview.order]);

  const filtered = useMemo(() => {
    return overview.voices.filter((voice: VoiceItem) => {
      if (installedOnly && !voice.installed) return false;
      if (lang && voice.lang !== lang) return false;
      if (engine && voice.engine !== engine) return false;
      if (query && !voice.name.toLowerCase().includes(query.toLowerCase()) && !voice.id.toLowerCase().includes(query.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [overview.voices, installedOnly, lang, engine, query]);

  return (
    <div className="space-y-4">
      <StatRow>
        <Stat label={t('stat_total')} value={overview.voices.length} tone="cyan" />
        <Stat label={t('stat_installed')} value={installed} tone="emerald" />
        <Stat label={t('stat_languages')} value={Object.keys(overview.langs).length} tone="purple" />
        <Stat label={t('stat_preferred')} value={Object.keys(overview.langPrefs).length} tone="amber" />
      </StatRow>

      <Panel title={t('order_title')}>
        <p className="mb-3 text-xs text-slate-500">{t('order_hint')}</p>
        <OrderList
          order={overview.order}
          fallback={overview.fallback}
          busy={busy}
          playing={playing}
          t={t}
          onChange={onSaveOrder}
          onPlay={onPlay}
        />
      </Panel>

      <Panel title={t('library_title')}>
        <div className="mb-3 grid gap-3 cq-sm:grid-cols-2 cq-lg:grid-cols-4">
          <Field label={t('filter_language')}>
            <select
              className={inputClass}
              value={lang}
              onChange={(event) => {
                setLang(event.target.value);
                setLimit(PAGE);
              }}
            >
              <option value="">{t('all')}</option>
              {Object.entries(overview.langs).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('filter_engine')}>
            <select
              className={inputClass}
              value={engine}
              onChange={(event) => {
                setEngine(event.target.value);
                setLimit(PAGE);
              }}
            >
              {ENGINES.map((value) => (
                <option key={value} value={value}>
                  {value ? t(`engine_${value}`) : t('all')}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('search')}>
            <input
              className={inputClass}
              value={query}
              maxLength={60}
              onChange={(event) => {
                setQuery(event.target.value);
                setLimit(PAGE);
              }}
            />
          </Field>
          <label className="flex items-end gap-2 pb-2 text-xs font-semibold text-slate-600">
            <input
              type="checkbox"
              checked={installedOnly}
              onChange={(event) => setInstalledOnly(event.target.checked)}
            />
            {t('installed_only')}
          </label>
        </div>

        {filtered.length === 0 ? (
          <Empty>{t('empty')}</Empty>
        ) : (
          <List>
            {filtered.slice(0, limit).map((voice) => (
              <VoiceRow
                key={voice.id}
                voice={voice}
                inOrder={ids.has(voice.id)}
                busy={busy}
                playing={playing === voice.id}
                t={t}
                onPlay={onPlay}
                onDownload={onDownload}
                onRemove={onRemove}
                onAdd={(id) => onSaveOrder([...Array.from(ids), id])}
                onPrefer={onPrefer}
              />
            ))}
          </List>
        )}
        {filtered.length > limit ? (
          <div className="mt-3 flex justify-center">
            <Btn tone="slate" onClick={() => setLimit((value) => value + PAGE)}>
              {t('more', { count: filtered.length - limit })}
            </Btn>
          </div>
        ) : null}
      </Panel>
    </div>
  );
};
