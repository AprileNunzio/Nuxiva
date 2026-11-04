import React from 'react';
import { FolderOpen } from 'lucide-react';
import { Empty, List, Panel, Pill, Row } from '../../shared/kit';
import { ShareFolder } from '../types';

interface FoldersPanelProps {
  readonly folders: readonly ShareFolder[];
  readonly root: string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const FoldersPanel: React.FC<FoldersPanelProps> = ({ folders, root, t }) => (
  <Panel title={t('folders_title')} icon={<FolderOpen className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
    <p className="mb-3 break-all text-[11px] text-slate-500">{root}</p>
    {folders.length === 0 ? (
      <Empty>{t('folders_empty')}</Empty>
    ) : (
      <List>
        {folders.map((folder) => (
          <Row key={folder.kind} actions={<Pill tone="cyan">{t('items', { n: folder.count })}</Pill>}>
            <b>{folder.name}</b>
            <p className="text-xs text-slate-600">{folder.description}</p>
            {folder.latest.length > 0 ? <p className="mt-1 truncate text-[11px] text-slate-500">{folder.latest.join(' · ')}</p> : null}
          </Row>
        ))}
      </List>
    )}
  </Panel>
);
