import React from 'react';
import { Layers } from 'lucide-react';
import { List, Panel, Pill, Row } from '../../shared/kit';
import { McpArea } from '../types';
import { Translate } from './shared';

interface Props {
  readonly areas: readonly McpArea[];
  readonly t: Translate;
}

export const AreasPanel: React.FC<Props> = ({ areas, t }) => (
  <Panel title={t('areas_title')} icon={<Layers className="h-4 w-4 text-primary" aria-hidden="true" />}>
    <p className="mb-2 text-xs text-on-surface-variant">{t('areas_hint')}</p>
    <List>
      {areas.map((area) => (
        <Row key={area.server} actions={<Pill tone={area.mode === 'mcp' ? 'emerald' : 'slate'}>{t(`area_mode_${area.mode}`)}</Pill>}>
          <b className="font-mono text-xs">{area.server}</b>
          <span className="ml-2 text-[11px] text-on-surface-variant">{t('server_tools', { n: area.tools })}</span>
        </Row>
      ))}
    </List>
  </Panel>
);
