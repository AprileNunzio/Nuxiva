type Translate = (key: string, params?: Record<string, string | number>) => string;

export const gestureLabel = (t: Translate, id: string): string => {
  const [family, name] = id.split('.', 2);
  const familyText = t(`family_${family}`);
  return name ? `${familyText}: ${t(`name_${name}`)}` : familyText;
};

export const actionLabel = (t: Translate, id: string): string => {
  const key = `action_${id.replace(/\./g, '_')}`;
  const text = t(key);
  return text === key ? id : text;
};

export const contextLabel = (t: Translate, id: string): string => {
  const key = id === '*' ? 'context_any' : `context_${id.replace(/\./g, '_')}`;
  const text = t(key);
  return text === key ? id : text;
};
