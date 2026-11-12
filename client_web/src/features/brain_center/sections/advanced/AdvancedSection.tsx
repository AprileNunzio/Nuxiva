import React from 'react';
import { Bot } from 'lucide-react';
import { useSectionText } from '../../core/i18n';
import { Card, Row, SectionHeader } from '../../ui/primitives';
import { FreeMatrixCard } from './FreeMatrixCard';

export const AdvancedSection: React.FC = () => {
  const { t } = useSectionText('advanced');
  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      <FreeMatrixCard />
      <Card flush>
        <Row icon={Bot} title={t('agents_title')} description={t('agents_hint')} />
      </Card>
    </>
  );
};
