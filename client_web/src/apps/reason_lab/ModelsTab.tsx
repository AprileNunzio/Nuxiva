import React, { useState } from 'react';
import { Btn, Empty, Field, List, Panel, Row, inputClass } from '../shared/kit';
import { removeProfile, saveProfile } from './api';
import { BACKENDS } from './types';
import type { Backend, Profile } from './types';
import type { LabModel } from './useLab';

const BLANK: Profile = { id: '', name: '', backend: 'ollama', base_url: 'http://127.0.0.1:11434', model: '', timeout_seconds: 60 };
const SLUG = /^[a-z0-9][a-z0-9_]{2,39}$/;

export function ModelsTab({ model: m }: { model: LabModel }) {
  const { t } = m;
  const [form, setForm] = useState<Profile>(BLANK);
  const valid = SLUG.test(form.id) && form.name.trim() !== '' && form.model.trim() !== '' && form.base_url.trim() !== '';
  const set = <K extends keyof Profile>(field: K, value: Profile[K]) => setForm(previous => ({ ...previous, [field]: value }));

  const submit = async () => {
    const saved = await m.run(() => saveProfile({ ...form, name: form.name.trim(), model: form.model.trim(), base_url: form.base_url.trim() }));
    if (saved) {
      m.profilesResource.reload();
      setForm(BLANK);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Panel title={t('profile_form')}>
        <p className="mb-3 text-xs text-on-surface-variant">{t('profile_hint')}</p>
        <form className="grid gap-3 cq-lg:grid-cols-2" onSubmit={event => { event.preventDefault(); if (valid) void submit(); }}>
          <Field label={t('profile_id')}><input className={inputClass} value={form.id} maxLength={40} onChange={event => set('id', event.target.value.toLowerCase())} /></Field>
          <Field label={t('profile_name')}><input className={inputClass} value={form.name} maxLength={80} onChange={event => set('name', event.target.value)} /></Field>
          <Field label={t('backend')}>
            <select className={inputClass} value={form.backend} onChange={event => set('backend', event.target.value as Backend)}>
              {BACKENDS.map(item => <option key={item} value={item}>{t(`backend_${item}`)}</option>)}
            </select>
          </Field>
          <Field label={t('base_url')}><input className={inputClass} value={form.base_url} maxLength={256} inputMode="url" onChange={event => set('base_url', event.target.value)} /></Field>
          <Field label={t('model')}><input className={inputClass} value={form.model} maxLength={100} onChange={event => set('model', event.target.value)} /></Field>
          <Field label={t('timeout')}><input className={inputClass} type="number" min={5} max={300} value={form.timeout_seconds} onChange={event => set('timeout_seconds', Number(event.target.value) || 60)} /></Field>
          <div className="cq-lg:col-span-2"><Btn type="submit" busy={m.busy} disabled={!valid} tone="emerald">{t('save')}</Btn></div>
        </form>
      </Panel>
      <Panel title={t('profiles')}>
        {m.profiles.length === 0 ? <Empty>{t('no_profiles')}</Empty> : (
          <List>
            {m.profiles.map(profile => (
              <Row key={profile.id} actions={<>
                <Btn onClick={() => setForm(profile)}>{t('edit')}</Btn>
                <Btn tone="rose" onClick={() => void m.run(() => removeProfile(profile.id)).then(() => m.profilesResource.reload())}>{t('delete')}</Btn>
              </>}>
                <strong>{profile.name}</strong>
                <div className="break-all text-xs text-on-surface-variant">{t(`backend_${profile.backend}`)} · {profile.base_url} · {profile.model}</div>
              </Row>
            ))}
          </List>
        )}
      </Panel>
    </div>
  );
}
