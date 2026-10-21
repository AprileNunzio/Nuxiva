import React, { useState } from 'react';
import { Camera } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { DeviceInventory } from '../shared/components/DeviceInventory';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { usePairedNode } from '../shared/hooks/usePairedNode';
import { ControlsPanel } from './components/ControlsPanel';
import { LivePreview } from './components/LivePreview';
import { OptionsPanel } from './components/OptionsPanel';
import { PhotoGallery } from './components/PhotoGallery';
import { SourceList } from './components/SourceList';
import { useCameraOverview } from './hooks/useCameraOverview';
import { useCameraI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useCameraI18n();
  const local = scope === 'local';
  const { overview, refresh } = useCameraOverview(local);
  const { node } = usePairedNode(nodeId, scope);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [photoTick, setPhotoTick] = useState(0);
  const sources = overview?.sources ?? [];
  const selected = sources.find((s) => s.id === selectedId) ?? sources.find((s) => s.stream) ?? sources[0] ?? null;

  return (
    <ModuleFrame icon={Camera} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && (
        <>
          <Notice tone="info">{t('notice_paired')}</Notice>
          <DeviceInventory
            title={t('inventory_title')}
            devices={[...(node?.hardware?.cameras ?? []), ...(node?.hardware?.irCamera ? [t('ir_sensor')] : [])]}
            emptyLabel={t('inventory_empty')}
          />
        </>
      )}
      {local && overview && (
        <>
          {(!overview.tools.ffmpeg || !overview.tools.v4l2) && (
            <Notice tone="warn">{t('tools_missing', { tools: [!overview.tools.ffmpeg && 'ffmpeg', !overview.tools.v4l2 && 'v4l2-ctl'].filter(Boolean).join(', ') })}</Notice>
          )}
          {overview.problems.map((problem) => (
            <Notice key={problem} tone="warn">
              {problem}
            </Notice>
          ))}
          {sources.length === 0 ? (
            <Notice tone="info">{t('sources_empty')}</Notice>
          ) : (
            <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
              <SourceList sources={sources} selected={selected?.id ?? null} onSelect={setSelectedId} />
              {selected && (
                <div className="flex min-w-0 flex-col gap-4">
                  <LivePreview source={selected} onPhoto={() => setPhotoTick((value) => value + 1)} />
                  <div className="grid gap-4 xl:grid-cols-2">
                    <OptionsPanel source={selected} onSaved={refresh} />
                    {selected.controllable && <ControlsPanel sourceId={selected.id} />}
                  </div>
                  <PhotoGallery sourceId={selected.id} refreshKey={photoTick} />
                </div>
              )}
            </div>
          )}
        </>
      )}
    </ModuleFrame>
  );
};

export default View;
