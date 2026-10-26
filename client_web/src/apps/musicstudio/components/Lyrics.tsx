import React, { useEffect, useState } from 'react';
import { FileAudio, Languages, Mic2, Wand2 } from 'lucide-react';
import { addVocals, importAudio, listSources, translateProject, writeLyrics, type SourceFile } from '../api';
import { Btn, cx, Field, selectClass, inputClass } from './ui';
import type { Catalog, Project } from '../types';
import type { Studio } from '../useStudio';

interface Props {
  readonly studio: Studio;
  readonly project: Project;
  readonly catalog: Catalog;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const KINDS = ['produzioni', 'musica', 'scambio'];

const NOTICE_KEYS = new Set(['original_lyrics', 'lyrics_from_library', 'lyrics_from_web', 'lyrics_not_found', 'translation_failed']);

export const Lyrics: React.FC<Props> = ({ studio, project, catalog, t }) => {
  const [lang, setLang] = useState('en');
  const [sing, setSing] = useState(true);
  const [draft, setDraft] = useState(project.lyrics.text);
  const [topic, setTopic] = useState('');
  const [working, setWorking] = useState('');
  const [kind, setKind] = useState(KINDS[0]);
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [open, setOpen] = useState(false);
  const languages = Object.entries(catalog.languages);

  useEffect(() => setDraft(project.lyrics.text), [project.id, project.lyrics.text]);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    listSources(kind).then((rows) => alive && setFiles(rows)).catch(() => alive && setFiles([]));
    return () => { alive = false; };
  }, [open, kind]);

  const run = async (name: string, job: () => Promise<Project>) => {
    setWorking(name);
    try {
      await studio.replace(await job());
    } catch {
      studio.setError(name);
    } finally {
      setWorking('');
    }
  };

  const notice = project.job.notice;
  const translations = Object.entries(project.lyrics.translations);

  return (
    <div className="flex flex-col gap-4 p-3">
      {NOTICE_KEYS.has(notice) && (
        <div className={cx('rounded-xl border px-3 py-2 text-xs', notice === 'lyrics_not_found' || notice === 'translation_failed' ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800')}>
          {t(`notice_${notice}`)}
        </div>
      )}
      <section className="space-y-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('lyrics')}</div>
        <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={9} maxLength={4000} aria-label={t('lyrics')} placeholder={t('lyrics_placeholder')} className={cx(inputClass, 'w-full resize-y font-mono leading-relaxed')} />
        <div className="grid grid-cols-2 gap-1.5">
          <Field label={t('language')}>
            <select value={lang} onChange={(e) => setLang(e.target.value)} className={selectClass}>
              {languages.map(([id, name]) => (
                <option key={id} value={id}>{name}</option>
              ))}
            </select>
          </Field>
          <Field label={t('write_topic')}>
            <input value={topic} maxLength={300} onChange={(e) => setTopic(e.target.value)} className={inputClass} placeholder={t('write_topic_hint')} />
          </Field>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Btn
            disabled={topic.trim().length < 3 || !!working}
            onClick={async () => {
              setWorking('lyrics');
              try {
                setDraft(await writeLyrics(topic, project.genre, lang));
              } catch {
                studio.setError('lyrics');
              } finally {
                setWorking('');
              }
            }}
          >
            <Wand2 size={13} />
            {t('write_lyrics')}
          </Btn>
          <Btn tone="accent" disabled={draft.trim().length < 3 || !!working} onClick={() => void run('vocals', () => addVocals(project.id, draft, lang, ''))}>
            <Mic2 size={13} />
            {t('sing_it')}
          </Btn>
        </div>
      </section>
      <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-3">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('translate')}</div>
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" checked={sing} onChange={(e) => setSing(e.target.checked)} className="accent-violet-600" />
          {t('translate_sing')}
        </label>
        <Btn tone="soft" disabled={!project.lyrics.text || !!working} onClick={() => void run('translate', () => translateProject(project.id, lang, sing, ''))}>
          <Languages size={13} />
          {t('translate_go', { lang: catalog.languages[lang] ?? lang })}
        </Btn>
        {translations.map(([code, body]) => (
          <details key={code} className="rounded-lg bg-slate-50 px-2 py-1.5 text-xs">
            <summary className="cursor-pointer font-medium text-slate-700">{catalog.languages[code] ?? code}</summary>
            <pre className="mt-1 whitespace-pre-wrap font-sans text-slate-600">{body}</pre>
          </details>
        ))}
      </section>
      <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-3">
        <div className="flex items-center justify-between">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('import')}</div>
          <Btn onClick={() => setOpen((v) => !v)}>
            <FileAudio size={13} />
            {open ? t('close') : t('import_browse')}
          </Btn>
        </div>
        {open && (
          <>
            <select aria-label={t('import')} value={kind} onChange={(e) => setKind(e.target.value)} className={cx(selectClass, 'w-full')}>
              {KINDS.map((k) => (
                <option key={k} value={k}>{t(`source_${k}`)}</option>
              ))}
            </select>
            <ul className="max-h-48 space-y-1 overflow-y-auto">
              {files.length === 0 && <li className="py-3 text-center text-xs text-slate-400">{t('import_empty')}</li>}
              {files.map((file) => (
                <li key={file.path}>
                  <button
                    type="button"
                    disabled={!!working}
                    onClick={() => void run('import', () => importAudio(project.id, kind, file.path))}
                    className="w-full truncate rounded-md px-2 py-1 text-left text-xs text-slate-700 hover:bg-violet-50"
                  >
                    {file.name}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
      {working && <div className="text-center text-xs text-violet-600">{t('working')}</div>}
    </div>
  );
};
