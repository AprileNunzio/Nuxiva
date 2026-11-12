import React, { FormEvent, useState } from 'react';
import { Plus } from 'lucide-react';
import { Btn, Field, Panel, inputClass } from '../../shared/kit';
import { createProfile } from '../api';
import { VpnDraft } from '../types';

const KINDS = ['wireguard_server', 'openvpn', 'tailscale', 'zerotier'] as const;
type Kind = (typeof KINDS)[number];

interface CreateProfileProps {
  readonly tools: Readonly<Record<string, boolean>>;
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

function draftOf(kind: Kind, name: string, payload: string, secret: string): VpnDraft {
  if (kind === 'wireguard_server') {
    return { kind: 'wireguard', role: 'server', name };
  }
  if (kind === 'openvpn') {
    return { kind: 'openvpn', role: 'client', name, import: payload };
  }
  if (kind === 'tailscale') {
    return { kind: 'tailscale', role: 'client', name, settings: {}, secrets: { auth_key: secret } };
  }
  return { kind: 'zerotier', role: 'client', name, settings: { network_id: payload } };
}

export const CreateProfile: React.FC<CreateProfileProps> = ({ tools, busy, t, run }) => {
  const [kind, setKind] = useState<Kind>('wireguard_server');
  const [name, setName] = useState('');
  const [payload, setPayload] = useState('');
  const [secret, setSecret] = useState('');
  const tool = kind === 'wireguard_server' ? 'wireguard' : kind;
  const ready = name.trim().length > 0 && (kind === 'wireguard_server' || (kind === 'tailscale' ? secret.trim() : payload.trim()));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!ready) {
      return;
    }
    const done = await run(() => createProfile(draftOf(kind, name.trim(), payload.trim(), secret.trim())), 'vpn_create_failed');
    if (done !== null) {
      setName('');
      setPayload('');
      setSecret('');
    }
  };

  return (
    <Panel title={t('create_title')} icon={<Plus className="h-4 w-4 text-cyan-700" aria-hidden="true" />}>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label={t('field_kind')}>
          <select className={inputClass} value={kind} onChange={(event) => setKind(event.target.value as Kind)}>
            {KINDS.map((item) => (
              <option key={item} value={item}>
                {t(`kind_${item}`)}
              </option>
            ))}
          </select>
        </Field>
        {tools[tool] === false ? <p className="text-xs text-amber-700">{t('tool_missing', { tool })}</p> : null}
        <Field label={t('field_name')}>
          <input className={inputClass} value={name} maxLength={48} onChange={(event) => setName(event.target.value)} required />
        </Field>
        {kind === 'openvpn' ? (
          <Field label={t('field_ovpn')}>
            <textarea className={`${inputClass} h-32 font-mono text-xs`} value={payload} onChange={(event) => setPayload(event.target.value)} required />
          </Field>
        ) : null}
        {kind === 'zerotier' ? (
          <Field label={t('field_network')}>
            <input className={`${inputClass} font-mono`} value={payload} maxLength={16} onChange={(event) => setPayload(event.target.value)} required />
          </Field>
        ) : null}
        {kind === 'tailscale' ? (
          <Field label={t('field_auth_key')}>
            <input className={`${inputClass} font-mono`} type="password" autoComplete="off" value={secret} onChange={(event) => setSecret(event.target.value)} required />
          </Field>
        ) : null}
        <Btn type="submit" busy={busy} disabled={!ready}>
          {t('create')}
        </Btn>
      </form>
    </Panel>
  );
};
