type Translate = (key: string, params?: Record<string, string | number>) => string;

export function errorTitle(t: Translate, code: string): string {
  const key = `error_${code}`;
  const text = t(key);
  return text === key ? t('error_unknown_code', { code }) : text;
}

export function serverCodeLabel(t: Translate, code: string): string {
  const key = `server_${code}`;
  const text = t(key);
  return text === key ? code : `${text} (${code})`;
}
