import React from 'react';
import { Btn, Empty, List, Pill, Row, formatTime } from '../../shared/kit';
import { FlowVersion } from '../types';

interface VersionsProps {
  readonly versions: readonly FlowVersion[];
  readonly lang: string;
  readonly busy: boolean;
  readonly t: (key: string) => string;
  readonly onRollback: (version: number) => void;
}

export const Versions: React.FC<VersionsProps> = ({ versions, lang, busy, t, onRollback }) =>
  versions.length === 0 ? (
    <Empty>{t('no_versions')}</Empty>
  ) : (
    <List>
      {versions.map((item, index) => (
        <Row
          key={item.version}
          actions={
            index === 0 ? (
              <Pill tone="emerald">{t('active')}</Pill>
            ) : (
              <Btn tone="amber" busy={busy} onClick={() => onRollback(item.version)}>
                {t('restore')}
              </Btn>
            )
          }
        >
          <b>v{item.version}</b> <span className="text-xs text-slate-500">{formatTime(item.at, lang)} · {item.author}</span>
          {item.auto ? <Pill tone="rose">{t('auto')}</Pill> : null}
          <p className="text-xs text-slate-600">{item.note}</p>
        </Row>
      ))}
    </List>
  );
