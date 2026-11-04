import React, { useMemo } from 'react';
import { useScopedI18n, getScopedString } from '../../shared/i18n/useScopedI18n';
import { ApplicationCatalog } from '../../app_shell/window_manager/ApplicationCatalog';
import { appRegistry } from '../../app_shell/window_manager/registry';
import { isApplication } from '../../app_shell/window_manager/app_scanner';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { useAssistantIdentity } from '../../shared/identity/IdentityContext';

export function View() {
  const { openApp } = useOSApp();
  const { t, lang } = useScopedI18n('apps/applications');
  const assistant = useAssistantIdentity();

  // Usa lo scanner dedicato per identificare solo le vere applicazioni
  const apps = useMemo(() => {
    return appRegistry.filter(
      (app) => app.target !== 'node' && isApplication(app) && app.id !== 'applications'
    );
  }, []);

  const categories: Record<string, string> = {
    media: t('category_media'),
    creativity: t('category_creativity'),
    productivity: t('category_productivity'),
    intelligence: t('category_intelligence'),
    security: t('category_security'),
    development: t('category_development'),
    spaces: t('category_spaces'),
    system: t('category_system'),
  };

  const getAppTitle = (app: (typeof apps)[number]) =>
    app.id === 'explorer' ? assistant.name : getScopedString(app.scope, lang, 'title', app.name);

  const getAppDesc = (app: (typeof apps)[number]) =>
    getScopedString(app.scope, lang, 'description', ((app as unknown as Record<string, unknown>).description as string) || '');

  const items = useMemo(() => {
    return apps.map((app) => ({
      id: app.id,
      label: getAppTitle(app),
      description: getAppDesc(app),
      category: app.category || 'system',
      icon: app.iconUrl,
      symbol: (app as unknown as Record<string, unknown>).icon as string | undefined,
      active: true,
    }));
  }, [apps, lang, assistant.name]);

  return (
    <ApplicationCatalog
      lang={lang}
      labels={{
        search: t('search'),
        clearSearch: t('clear_search'),
        categories: t('navigation'),
        all: t('all_categories'),
        empty: t('empty'),
        emptyHint: t('empty_hint'),
        stateFilter: t('state_filter'),
        allStates: t('all_states'),
        on: t('running'),
        off: t('stopped'),
        reset: t('reset_filters'),
        pinToDesktop: t('pin_to_desktop'),
        unpinFromDesktop: t('unpin_from_desktop'),
        open: t('open_app'),
      }}
      categories={categories}
      items={items}
      onOpen={(id) => openApp({ appId: id })}
    />
  );
}

export default View;
