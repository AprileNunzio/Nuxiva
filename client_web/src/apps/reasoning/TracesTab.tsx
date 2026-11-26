import React from 'react';
import { Empty, List, Panel, Pill, Row } from '../shared/kit';
import type { Trace } from './types';
import type { EngineModel } from './useEngine';

const TONE = { shadow: 'amber', active: 'emerald', fallback: 'slate', error: 'rose' } as const;

function verdict(trace: Trace) {
  if (trace.kind !== 'shadow') return null;
  if (trace.legacy == null) return 'not_comparable';
  return trace.agreed ? 'agreed' : 'disagreed';
}

export function TracesTab({ model: m }: { model: EngineModel }) {
  const { t } = m;
  return (
    <Panel title={t('traces_title')}>
      <p className="mb-3 text-xs text-on-surface-variant">{t('traces_hint')}</p>
      {m.traces.length === 0 ? <Empty>{t('no_traces')}</Empty> : (
        <List>
          {m.traces.map(trace => {
            const result = verdict(trace);
            return (
              <Row key={`${trace.at}-${trace.intent}`} actions={<>
                <Pill tone={TONE[trace.kind]}>{t(`kind_${trace.kind}`)}</Pill>
                {result ? <Pill tone={result === 'agreed' ? 'emerald' : result === 'disagreed' ? 'rose' : 'slate'}>{t(result)}</Pill> : null}
              </>}>
                <strong className="break-all">{trace.intent || t('no_intent')}</strong>
                <div className="break-all text-xs text-on-surface-variant">
                  {m.time(trace.at)} · {trace.language || '-'} · {trace.capabilities.join(' → ') || trace.code || '-'}
                </div>
                <div className="text-xs text-on-surface-variant">
                  {t('trace_cost', { tokens: trace.tokens, ms: trace.latency_ms })}{trace.cached ? ` · ${t('cached')}` : ''}
                  {trace.legacy ? ` · ${t('legacy')}: ${trace.legacy.join(', ')}` : ''}
                </div>
              </Row>
            );
          })}
        </List>
      )}
    </Panel>
  );
}
