import React, { useState } from 'react';
import { ArrowLeft, Download, Folder } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, inputClass, Loading, Panel, Unreachable } from '../../shared/kit';
import { sendJson } from '../../shared/http';
import { useAction, useResource } from '../../shared/useResource';

interface Share {
  readonly id: string;
  readonly name: string;
  readonly can_create: boolean;
}

interface Listing {
  readonly items: ReadonlyArray<{ readonly name: string; readonly is_dir: boolean }>;
}

const Directory: React.FC<{ readonly share: Share; readonly close: () => void }> = ({ share, close }) => {
  const { t } = useScopedI18n('core_apps/shares');
  const [parts, setParts] = useState<string[]>([]);
  const [name, setName] = useState('');
  const [createFailed, setCreateFailed] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadFailed, setUploadFailed] = useState(false);
  const base = `/api/shares/scoped/${encodeURIComponent(share.id)}`;
  const url = `${base}?subpath=${encodeURIComponent(parts.join('/'))}`;
  const listing = useResource<Listing>(url);
  const { busy, run } = useAction(listing.reload);
  const back = () => parts.length ? setParts(parts.slice(0, -1)) : close();
  const current = !listing.error && listing.dataUrl === url ? listing.data : null;
  const create = async (event: React.FormEvent) => {
    event.preventDefault();
    const query = new URLSearchParams({ name: name.trim(), subpath: parts.join('/') });
    const result = await run(() => sendJson(`${base}/folders?${query}`, 'POST'));
    setCreateFailed(result === null);
    if (result) setName('');
  };
  const upload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    const form = event.currentTarget;
    const query = new URLSearchParams({ name: file.name, subpath: parts.join('/') });
    const result = await run(async () => {
      const response = await fetch(`${base}/file?${query}`, {
        method: 'PUT',
        headers: { 'X-Nuxiva-Request': '1' },
        body: file,
      });
      if (!response.ok) throw new Error(`share_upload_http_${response.status}`);
      return true;
    });
    setUploadFailed(result === null);
    if (result) {
      form.reset();
      setFile(null);
    }
  };

  return (
    <Panel title={[share.name, ...parts].join(' / ')}>
      <div className="mb-3 flex flex-wrap gap-2">
        <Btn onClick={back}><ArrowLeft className="h-4 w-4" aria-hidden="true" />{t('scoped_back')}</Btn>
        <Btn onClick={listing.reload}>{t('scoped_refresh')}</Btn>
      </div>
      {share.can_create && current && (
        <form className="mb-3 flex flex-wrap gap-2" onSubmit={(event) => void create(event)}>
          <label className="min-w-0 flex-1 text-sm">
            {t('scoped_folder_name')}
            <input className={inputClass} value={name} onChange={(event) => setName(event.target.value)}
              required maxLength={80} />
          </label>
          <Btn type="submit" busy={busy} disabled={!name.trim()}>{t('scoped_create_folder')}</Btn>
          {createFailed && <p role="alert" className="w-full text-sm text-error">{t('scoped_create_failed')}</p>}
        </form>
      )}
      {share.can_create && current && (
        <form className="mb-3 flex flex-wrap gap-2" onSubmit={(event) => void upload(event)}>
          <label className="min-w-0 flex-1 text-sm">
            {t('scoped_upload_file')}
            <input className={inputClass} type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required />
          </label>
          <Btn type="submit" busy={busy} disabled={!file}>{t('scoped_upload_submit')}</Btn>
          {uploadFailed && <p role="alert" className="w-full text-sm text-error">{t('scoped_upload_failed')}</p>}
        </form>
      )}
      {listing.error ? <Unreachable label={t('scoped_unavailable')} /> :
        !current ? <Loading label={t('loading')} /> :
        !current.items.length ? <Empty>{t('scoped_empty')}</Empty> :
          <ul className="divide-y divide-outline/30">
            {current.items.map((item) => (
              <li key={item.name} className="min-w-0 py-2">
                {item.is_dir ? (
                  <Btn onClick={() => setParts([...parts, item.name])}>
                    <Folder className="h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="break-all">{item.name}</span>
                  </Btn>
                ) : (
                  <a className="flex min-h-11 items-center gap-2 break-all text-primary underline"
                    href={`${base}/file?path=${encodeURIComponent([...parts, item.name].join('/'))}`}
                    download={item.name}>
                    <Download className="h-4 w-4 shrink-0" aria-hidden="true" />{item.name}
                  </a>
                )}
              </li>
            ))}
          </ul>}
    </Panel>
  );
};

export const ScopedShares: React.FC = () => {
  const { t } = useScopedI18n('core_apps/shares');
  const resource = useResource<{ readonly shares: Share[] }>('/api/shares/scoped');
  const [selected, setSelected] = useState<string | null>(null);
  const available = resource.error ? [] : resource.data?.shares ?? [];
  const share = available.find((item) => item.id === selected);
  return (
    <AppFrame title={t('title')} description={t('scoped_description')} onReload={resource.reload}>
      {resource.error ? <Unreachable label={t('scoped_unavailable')} /> :
        !resource.data ? <Loading label={t('loading')} /> :
        share ? <Directory key={share.id} share={share} close={() => setSelected(null)} /> :
        available.length ? (
          <ul className="grid gap-3 sm:grid-cols-2">
            {available.map((item) => (
              <li key={item.id}><Btn onClick={() => setSelected(item.id)}>
                <Folder className="h-4 w-4 shrink-0" aria-hidden="true" />{item.name}
              </Btn></li>
            ))}
          </ul>
        ) : <Empty>{t('scoped_no_shares')}</Empty>}
    </AppFrame>
  );
};
