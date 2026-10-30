import React from 'react';
import { ArrowRight } from 'lucide-react';
import { useBrainText, useSectionText } from '../../core/i18n';
import { RoleState } from '../../core/types';
import { Badge, Button } from '../../ui/primitives';
import { roleIcon } from '../../ui/roleIcons';

interface NowCardProps {
  readonly kind: string;
  readonly role: RoleState | null;
  readonly onChange: () => void;
}

export const NowCard: React.FC<NowCardProps> = ({ kind, role, onChange }) => {
  const { t } = useSectionText('overview');
  const base = useBrainText();
  const Icon = roleIcon(kind);
  const active = role?.active ?? null;
  const backups = Math.max(0, (role?.effective.length ?? 0) - 1);
  return (
    <section className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-900">{t(`now_${kind}`)}</h3>
          <p className="text-xs text-slate-500">{t(`now_${kind}_hint`)}</p>
        </div>
      </div>
      <div className="min-w-0">
        <p className="truncate text-xl font-semibold tracking-tight text-slate-900" aria-live="polite">
          {active ? active.model : base.t('none_available')}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {active && <Badge tone={active.origin === 'cloud' ? 'info' : 'success'}>{base.t(`origin_${active.origin}`)}</Badge>}
          {active?.provider && <Badge>{active.provider}</Badge>}
          <Badge tone={backups > 0 ? 'success' : 'warning'}>{backups > 0 ? t('backups', { n: backups }) : t('no_backups')}</Badge>
          {role && <Badge>{base.t(role.custom ? 'mode_custom' : 'mode_auto')}</Badge>}
        </div>
      </div>
      <div className="mt-auto">
        <Button icon={ArrowRight} onClick={onChange}>
          {t('change')}
        </Button>
      </div>
    </section>
  );
};
