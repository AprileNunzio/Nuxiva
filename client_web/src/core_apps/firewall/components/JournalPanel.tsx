import React from 'react';
import { ScrollText } from 'lucide-react';
import { Empty, List, Panel, Pill, Row, formatTime } from '../../shared/kit';
import { JournalState } from '../types';
import { Translate } from './shared';

const SHOWN = 30;

interface Props {
  readonly journal: JournalState | null;
  readonly lang: string;
  readonly t: Translate;
}

export const JournalPanel: React.FC<Props> = ({ journal, lang, t }) => {
  const entries = journal ? [...journal.entries].slice(-SHOWN).reverse() : [];
  return (
    <Panel
      title={t('journal_title')}
      icon={<ScrollText className="h-4 w-4 text-slate-700" aria-hidden="true" />}
      actions={journal ? <Pill tone={journal.intact ? 'emerald' : 'rose'}>{t(journal.intact ? 'journal_intact' : 'journal_broken')}</Pill> : null}
    >
      {entries.length === 0 ? (
        <Empty>{t('journal_empty')}</Empty>
      ) : (
        <List>
          {entries.map((entry) => (
            <Row key={entry.hash} actions={<Pill tone={entry.ok ? 'emerald' : 'rose'}>{t(entry.ok ? 'done' : 'failed')}</Pill>}>
              <b>{entry.action}</b>
              <span className="ml-2 font-mono text-xs text-slate-600">{entry.target}</span>
              <p className="text-[11px] text-slate-500">{formatTime(entry.at, lang)} · {entry.by}{entry.detail ? ` · ${entry.detail}` : ''}</p>
            </Row>
          ))}
        </List>
      )}
    </Panel>
  );
};
