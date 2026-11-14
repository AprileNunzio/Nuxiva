import React, { useState } from 'react';
import { Loader2, ShieldCheck } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { LinkNode } from '../data/linkApi';
import { ELEVATED_GRANTS, NodeProfile, PROFILES, setNodeTrust } from '../data/trustApi';
import { LinksHandle } from '../hooks/useLinks';
import { useLinkI18n } from '../scope';

const chip = 'rounded-full border px-2 py-0.5 font-mono text-[10px]';

const ScopeList: React.FC<{ readonly title: string; readonly items: readonly string[]; readonly tone: string }> = ({ title, items, tone }) =>
  items.length === 0 ? null : (
    <div className="mt-3">
      <p className="mb-1 text-[11px] font-semibold text-slate-300">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span key={item} className={`${chip} ${tone}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );

export const TrustPanel: React.FC<{ readonly node: LinkNode; readonly handle: LinksHandle }> = ({ node, handle }) => {
  const { t } = useLinkI18n();
  const trust = node.trust;
  const [profile, setProfile] = useState<NodeProfile>(trust.profile);
  const [allow, setAllow] = useState(trust.allowed);
  const [grants, setGrants] = useState<readonly string[]>(trust.grants);
  const effectiveAllow = profile === 'satellite' ? false : allow;
  const dirty = profile !== trust.profile || effectiveAllow !== trust.allowed || grants.join() !== trust.grants.join();

  const toggleGrant = (grant: string) =>
    setGrants((current) => (current.includes(grant) ? current.filter((g) => g !== grant) : [...current, grant].sort()));

  return (
    <Panel title={t('trust_title')}>
      <div className="flex flex-wrap items-center gap-2">
        <ShieldCheck className={`h-4 w-4 ${trust.mode === 'second_server' ? 'text-amber-300' : 'text-emerald-300'}`} aria-hidden="true" />
        <span className="text-sm font-semibold text-slate-100">{t(`trust_mode_${trust.mode}`)}</span>
        {trust.fingerprint && <span className="font-mono text-[11px] text-slate-400">{t('trust_fingerprint')} {trust.fingerprint}</span>}
      </div>
      {trust.legacy ? (
        <p className="mt-3 rounded-xl border border-amber-400/40 bg-amber-400/5 p-3 text-xs text-amber-100">{t('trust_legacy')}</p>
      ) : (
        <>
          <label className="mt-3 block text-[11px] text-slate-400">
            {t('trust_profile')}
            <select
              value={profile}
              onChange={(event) => setProfile(PROFILES.find((p) => p === event.target.value) ?? 'satellite')}
              className="mt-1 block w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              {PROFILES.map((item) => (
                <option key={item} value={item}>
                  {t(`profile_${item}`)}
                </option>
              ))}
            </select>
          </label>
          <p className="mt-1 text-[11px] text-slate-400">{t(`profile_${profile}_hint`)}</p>
          {profile !== 'satellite' && (
            <label className="mt-3 flex items-start gap-2 text-xs text-slate-200">
              <input type="checkbox" checked={allow} onChange={(event) => setAllow(event.target.checked)} className="mt-0.5 h-4 w-4 accent-amber-400" />
              <span>
                {t('trust_allow')}
                <span className="block text-[11px] text-slate-500">{t('trust_allow_hint')}</span>
              </span>
            </label>
          )}
          {effectiveAllow && (
            <fieldset className="mt-3">
              <legend className="mb-1 text-[11px] font-semibold text-slate-300">{t('trust_grants')}</legend>
              <div className="flex flex-col gap-1">
                {ELEVATED_GRANTS.map((grant) => (
                  <label key={grant} className="flex items-center gap-2 text-xs text-slate-200">
                    <input type="checkbox" checked={grants.includes(grant)} onChange={() => toggleGrant(grant)} className="h-4 w-4 accent-rose-400" />
                    {t(`grant_${grant.replace('.', '_')}`)}
                    <span className="font-mono text-[10px] text-slate-500">{grant}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          <button
            type="button"
            disabled={!dirty || handle.busy !== null || (profile !== 'satellite' && !allow)}
            onClick={() =>
              void handle.run('trust', () => setNodeTrust(node.id, { profile, allow: effectiveAllow, grants: effectiveAllow ? grants : [] }), 'node_trust_failed')
            }
            className="mt-3 flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-100"
          >
            {handle.busy === 'trust' && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {t('trust_apply')}
          </button>
        </>
      )}
      {trust.cpuCores > 0 && <p className="mt-3 text-[11px] text-slate-400">{t('trust_resources', { cores: trust.cpuCores, ram: trust.ramMb })}</p>}
      {trust.effective.length === 0 && <p className="mt-3 text-xs text-slate-500">{t('trust_none')}</p>}
      <ScopeList title={t('trust_effective')} items={trust.effective} tone="border-emerald-400/40 text-emerald-200" />
      <ScopeList title={t('trust_denied')} items={trust.denied} tone="border-slate-700 text-slate-400" />
      <ScopeList title={t('trust_rejected')} items={trust.rejected} tone="border-rose-400/40 text-rose-200" />
    </Panel>
  );
};
