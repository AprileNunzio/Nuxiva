export type GuideSubTab = 'overview' | 'steps' | 'manifest' | 'code' | 'best_practices';

export type GuideModuleType = 'app' | 'engine' | 'agent' | 'plugin';

export type CodeFileType = 'manifest' | 'view' | 'i18n';

export interface DeveloperGuideProps {
  t: (key: string, params?: Record<string, any>) => string;
}
