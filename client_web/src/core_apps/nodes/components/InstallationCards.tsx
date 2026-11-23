import React, { useState } from 'react';
import { Box, Cpu, Laptop, LucideIcon, Monitor, Smartphone, Tablet, Terminal } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { LinksHandle } from '../../../node_apps/client_link/hooks/useLinks';
import { UsbPort } from '../types';
import { AndroidEnroll } from './AndroidEnroll';
import { PcLinkPanel } from './PcLinkPanel';
import { WindowsGuide } from './WindowsGuide';
import { DockerGuide } from './DockerGuide';
import { Esp32Guide } from './Esp32Guide';
import { MacosGuide } from './MacosGuide';
import { IosGuide } from './IosGuide';

export type PlatformId = 'windows' | 'android' | 'linux' | 'docker' | 'esp32' | 'macos' | 'ios';

const PENDING: ReadonlySet<PlatformId> = new Set<PlatformId>(['macos', 'ios']);

interface PlatformMeta {
  readonly id: PlatformId;
  readonly icon: LucideIcon;
  readonly titleKey: string;
  readonly badgeKey: string;
  readonly descKey: string;
  readonly stepCount: number;
}

const PLATFORMS: readonly PlatformMeta[] = [
  {
    id: 'windows',
    icon: Monitor,
    titleKey: 'install_windows_title',
    badgeKey: 'install_windows_badge',
    descKey: 'install_windows_desc',
    stepCount: 3,
  },
  {
    id: 'android',
    icon: Smartphone,
    titleKey: 'install_android_title',
    badgeKey: 'install_android_badge',
    descKey: 'install_android_desc',
    stepCount: 4,
  },
  {
    id: 'linux',
    icon: Terminal,
    titleKey: 'install_linux_title',
    badgeKey: 'install_linux_badge',
    descKey: 'install_linux_desc',
    stepCount: 3,
  },
  {
    id: 'docker',
    icon: Box,
    titleKey: 'install_docker_title',
    badgeKey: 'install_docker_badge',
    descKey: 'install_docker_desc',
    stepCount: 3,
  },
  {
    id: 'esp32',
    icon: Cpu,
    titleKey: 'install_esp32_title',
    badgeKey: 'install_esp32_badge',
    descKey: 'install_esp32_desc',
    stepCount: 3,
  },
  {
    id: 'macos',
    icon: Laptop,
    titleKey: 'install_macos_title',
    badgeKey: 'install_macos_badge',
    descKey: 'install_macos_desc',
    stepCount: 3,
  },
  {
    id: 'ios',
    icon: Tablet,
    titleKey: 'install_ios_title',
    badgeKey: 'install_ios_badge',
    descKey: 'install_ios_desc',
    stepCount: 4,
  },
];

export const InstallationCards: React.FC<{
  readonly links: LinksHandle;
  readonly usbPorts: UsbPort[] | null;
  readonly detectingUsb: boolean;
  readonly detectUsb: () => void;
}> = ({ links, usbPorts, detectingUsb, detectUsb }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [selected, setSelected] = useState<PlatformId>('windows');

  const activePlatform = PLATFORMS.find((p) => p.id === selected) ?? PLATFORMS[0];
  const ActiveIcon = activePlatform.icon;

  return (
    <section aria-label={t('install_platforms')} className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <p className="text-xs text-on-surface-variant">
          {t('install_platforms_intro')}
        </p>
      </div>

      <div
        role="tablist"
        aria-label={t('install_platforms')}
        className="grid grid-cols-2 gap-3 cq-sm:grid-cols-3 cq-lg:grid-cols-4 cq-2xl:grid-cols-7"
      >
        {PLATFORMS.map((platform) => {
          const Icon = platform.icon;
          const isActive = platform.id === selected;
          return (
            <button
              key={platform.id}
              type="button"
              role="tab"
              id={`tab-${platform.id}`}
              aria-selected={isActive}
              aria-controls={`panel-${platform.id}`}
              onClick={() => setSelected(platform.id)}
              className={`group relative flex flex-col items-start gap-2.5 rounded-3xl p-4 text-left transition-all ${
                isActive
                  ? 'bg-primary-container/30 ring-2 ring-primary shadow-sm'
                  : 'bg-surface-container-low hover:bg-surface-container hover:shadow-xs'
              }`}
            >
              <div className="flex w-full items-center justify-between">
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-2xl transition-colors ${
                    isActive
                      ? 'bg-primary text-on-primary'
                      : 'bg-surface-container-high text-on-surface-variant group-hover:text-primary'
                  }`}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                {isActive && (
                  <span className="flex h-2.5 w-2.5 rounded-full bg-primary" aria-hidden="true" />
                )}
              </div>
              <div className="min-w-0">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  {t(platform.badgeKey)}
                </span>
                <h3 className="truncate text-sm font-bold text-on-surface">
                  {t(platform.titleKey)}
                </h3>
              </div>
              <p className="line-clamp-2 text-[11px] leading-tight text-on-surface-variant">
                {t(platform.descKey)}
              </p>
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`panel-${activePlatform.id}`}
        aria-labelledby={`tab-${activePlatform.id}`}
        className="rounded-3xl border border-outline-variant/40 bg-surface-container-lowest p-5 shadow-sm sm:p-6"
      >
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/30 pb-4">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-container text-on-primary-container">
              <ActiveIcon className="h-6 w-6" aria-hidden="true" />
            </span>
            <div>
              <h2 className="text-lg font-bold text-on-surface">{t(activePlatform.titleKey)}</h2>
              <p className="text-xs text-on-surface-variant">
                {t(PENDING.has(activePlatform.id) ? 'install_pending' : 'install_steps_count', {
                  count: activePlatform.stepCount,
                })}{' '}
                · {t(activePlatform.badgeKey)}
              </p>
            </div>
          </div>
        </header>

        {selected === 'windows' && <WindowsGuide />}
        {selected === 'android' && <AndroidEnroll />}
        {selected === 'linux' && (
          <div className="space-y-4">
            <p className="text-sm text-on-surface-variant">{t('install_linux_guide')}</p>
            <PcLinkPanel handle={links} />
          </div>
        )}
        {selected === 'docker' && <DockerGuide />}
        {selected === 'esp32' && (
          <Esp32Guide usbPorts={usbPorts} detectingUsb={detectingUsb} detectUsb={detectUsb} />
        )}
        {selected === 'macos' && <MacosGuide />}
        {selected === 'ios' && <IosGuide />}
      </div>
    </section>
  );
};
