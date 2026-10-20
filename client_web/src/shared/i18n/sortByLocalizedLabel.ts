/** Locale-aware ordering without changing the scanner's registry. */
export function sortByLocalizedLabel<T>(items: readonly T[], locale: string, label: (item: T) => string): T[] {
  const collator = new Intl.Collator(locale, { sensitivity: 'base', numeric: true });
  return [...items].sort((left, right) => collator.compare(label(left), label(right)));
}
