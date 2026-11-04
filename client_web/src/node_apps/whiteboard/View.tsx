import React, { useState } from 'react';
import { Loader2, PenTool } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { BoardCanvas } from './components/BoardCanvas';
import { BoardToolbar } from './components/BoardToolbar';
import { OutputPanel } from './components/OutputPanel';
import { SavesPanel } from './components/SavesPanel';
import { useBoard } from './hooks/useBoard';
import { INKS, WIDTHS } from './render/primitives';
import { Tool, useBoardI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ scope = 'mesh' }) => {
  const { t } = useBoardI18n();
  const local = scope === 'local';
  const handle = useBoard(local);
  const [tool, setTool] = useState<Tool>('pen');
  const [color, setColor] = useState<string>(INKS[0]);
  const [width, setWidth] = useState<number>(WIDTHS.m);

  return (
    <ModuleFrame icon={PenTool} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && <Notice tone="info">{t('notice_paired')}</Notice>}
      {local && handle.view === null && (
        <p className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {t('loading')}
        </p>
      )}
      {local && handle.view && (
        <>
          <BoardToolbar handle={handle} tool={tool} color={color} width={width} onTool={setTool} onColor={setColor} onWidth={setWidth} />
          <BoardCanvas handle={handle} tool={tool} color={color} width={width} />
          {handle.view.says && (
            <p className="rounded-xl border border-cyan-400/30 bg-cyan-400/5 px-3 py-2 text-sm text-cyan-100" aria-live="polite">
              {t('says', { text: handle.view.says })}
            </p>
          )}
          <div className="grid gap-4 lg:grid-cols-2">
            <OutputPanel handle={handle} />
            <SavesPanel handle={handle} />
          </div>
        </>
      )}
    </ModuleFrame>
  );
};

export default View;
