import React from 'react';
import { MonitorSmartphone } from 'lucide-react';
import { useAction, usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { fetchTokenWidget, saveTokenWidget } from '../../core/displayApi';
import { useSectionText } from '../../core/i18n';
import { Card, Row, Switch } from '../../ui/primitives';

export const WidgetCard: React.FC = () => {
  const { t } = useSectionText('usage');
  const widget = usePolled(fetchTokenWidget, 'brain_widget_unavailable', true, 0);
  const action = useAction();
  const toggle = async (enabled: boolean) => {
    const result = await action.run('widget', () => saveTokenWidget(enabled), 'brain_widget_failed');
    if (result !== undefined) widget.setData(result);
  };
  return (
    <Card flush>
      <Row
        icon={MonitorSmartphone}
        title={t('widget_title')}
        description={t('widget_hint')}
        trailing={<Switch checked={widget.data === true} label={t('widget_title')} disabled={widget.data === null || action.busy !== null} onChange={(v) => void toggle(v)} />}
      />
    </Card>
  );
};
