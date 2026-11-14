import React, { useMemo } from 'react';
import { Gamepad2, Play } from 'lucide-react';
import { useScopedI18n, getScopedString } from '../../shared/i18n/useScopedI18n';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { getSubapps } from '../../app_shell/window_manager/app_scanner';
import { OSIcon3D } from '../../app_shell/OSIcon3D';

export function View() {
  const { t, lang } = useScopedI18n('subapps/giochi');
  const { openApp } = useOSApp();

  const games = useMemo(() => getSubapps('giochi'), []);

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface p-6 text-on-surface">
      <div className="mb-6 flex flex-col gap-1 border-b border-outline-variant/40 pb-4">
        <div className="flex items-center gap-2">
          <Gamepad2 className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold tracking-tight text-on-surface">{t('title')}</h1>
        </div>
        <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
        <span className="mt-1 text-xs font-semibold text-outline">
          {t('available', { count: games.length })}
        </span>
      </div>

      {games.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center text-outline">
          <Gamepad2 className="h-12 w-12 stroke-[1.5]" />
          <p className="text-sm">{t('empty')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 cq-sm:grid-cols-2 cq-lg:grid-cols-3">
          {games.map((game) => {
            const gameTitle = getScopedString(game.scope, lang, 'title', game.name);
            return (
              <div
                key={game.id}
                className="flex flex-col justify-between rounded-2xl border border-outline-variant/60 bg-surface-container p-4 shadow-sm transition-all hover:border-primary/40 hover:shadow-md"
              >
                <div className="flex items-center gap-3">
                  <OSIcon3D name={game.name} source={game.iconUrl} size="md" />
                  <div>
                    <h3 className="text-sm font-bold text-on-surface">{gameTitle}</h3>
                    <span className="text-xs text-outline">{game.id}</span>
                  </div>
                </div>

                <div className="mt-4 pt-2">
                  <button
                    type="button"
                    onClick={() => openApp({ appId: game.id })}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary shadow-sm transition-transform hover:opacity-95 active:scale-[0.98]"
                  >
                    <Play className="h-3.5 w-3.5 fill-current" />
                    <span>{t('play')}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default View;
