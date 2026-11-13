import React from 'react';
import { ScrollText } from 'lucide-react';
import { Empty, List, Panel, Pill, Row, Tone, formatTime } from '../../shared/kit';
import { McpAudit } from '../types';
import { Translate } from './shared';

const VERDICT_TONE: Record<string, Tone> = { completed: 'emerald', denied: 'amber', failed: 'rose', timed_out: 'rose' };
const SHOWN = 40;

interface Props {
  readonly audit: McpAudit | null;
  readonly lang: string;
  readonly t: Translate;
}

export const AuditPanel: React.FC<Props> = ({ audit, lang, t }) => {
  const records = audit ? [...audit.records].slice(-SHOWN).reverse() : [];
  return (
    <Panel
      title={t('audit_title')}
      icon={<ScrollText className="h-4 w-4 text-primary" aria-hidden="true" />}
      actions={audit ? <Pill tone={audit.intact ? 'emerald' : 'rose'}>{t(audit.intact ? 'audit_intact' : 'audit_broken')}</Pill> : null}
    >
      {audit ? <p className="mb-2 text-xs text-on-surface-variant">{t('audit_count', { n: audit.count })}</p> : null}
      {records.length === 0 ? (
        <Empty>{t('audit_empty')}</Empty>
      ) : (
        <List>
          {records.map((record) => (
            <Row key={record.hash} actions={<Pill tone={VERDICT_TONE[record.event.verdict] ?? 'slate'}>{t(`verdict_${record.event.verdict}`)}</Pill>}>
              <b className="font-mono text-xs">{record.event.server}.{record.event.tool}</b>
              <p className="text-[11px] text-on-surface-variant">
                {formatTime(record.event.ts_ms / 1000, lang)} · {record.event.agent} · {t(`risk_${record.event.risk}`)} · {record.event.duration_ms} ms
              </p>
            </Row>
          ))}
        </List>
      )}
    </Panel>
  );
};
