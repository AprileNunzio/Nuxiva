import React from 'react';
import { Wrench } from 'lucide-react';
import { Btn, Empty, List, Panel, Pill, Row, Tone } from '../../shared/kit';
import { McpTool } from '../types';
import { Translate } from './shared';

const STATE_TONE: Record<McpTool['state'], Tone> = { active: 'emerald', stale: 'amber', quarantined: 'rose' };
const SHOWN = 60;

interface Props {
  readonly tools: readonly McpTool[];
  readonly busy: boolean;
  readonly t: Translate;
  readonly onApprove: (id: string) => void;
}

export const ToolsPanel: React.FC<Props> = ({ tools, busy, t, onApprove }) => {
  const ordered = [...tools].sort((a, b) => Number(a.state === 'active') - Number(b.state === 'active') || a.id.localeCompare(b.id));
  return (
    <Panel title={t('tools_title')} icon={<Wrench className="h-4 w-4 text-primary" aria-hidden="true" />}>
      {ordered.length === 0 ? (
        <Empty>{t('tools_empty')}</Empty>
      ) : (
        <List>
          {ordered.slice(0, SHOWN).map((tool) => (
            <Row
              key={tool.id}
              actions={
                tool.state === 'active' ? (
                  <Pill tone="emerald">{t('tool_state_active')}</Pill>
                ) : (
                  <Btn tone={STATE_TONE[tool.state]} busy={busy} onClick={() => onApprove(tool.id)}>
                    {t('approve')}
                  </Btn>
                )
              }
            >
              <b className="font-mono text-xs">{tool.id}</b>
              <span className="ml-2 text-[11px] text-on-surface-variant">{t(`risk_${tool.risk}`)}</span>
              {tool.description ? <p className="line-clamp-2 text-[11px] text-on-surface-variant">{tool.description}</p> : null}
            </Row>
          ))}
        </List>
      )}
      {ordered.length > SHOWN ? <p className="mt-2 text-xs text-on-surface-variant">{t('tools_more', { n: ordered.length - SHOWN })}</p> : null}
    </Panel>
  );
};
