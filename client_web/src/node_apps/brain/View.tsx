import React from 'react';
import { Cpu } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { BrainCenter } from '../../features/brain_center/BrainCenter';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ scope = 'mesh' }) => {
  const { t } = useScopedI18n('node_apps/brain');
  return (
    <ModuleFrame icon={Cpu} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && <Notice tone="info">{t('notice_paired')}</Notice>}
      {scope === 'local' && (
        <div className="h-[min(85vh,960px)] min-h-[520px] overflow-hidden rounded-2xl border border-slate-200 shadow-xs">
          <BrainCenter />
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
