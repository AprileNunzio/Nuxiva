const dictionaries = import.meta.glob('/src/**/language/*.json', { eager: true, import: 'default' });
export const availableLanguages = [...new Set(Object.keys(dictionaries).map(path => path.split('/').pop()!.replace(/\.json$/, '')))].sort();
export function languageName(locale: string) {
  try { return new (Intl as any).DisplayNames([locale],{type:'language'}).of(locale); } catch { return locale.toUpperCase(); }
}
