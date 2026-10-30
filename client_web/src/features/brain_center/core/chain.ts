import { MAX_CHAIN, REF } from './parse';

export function moveItem(chain: readonly string[], index: number, delta: number): string[] {
  const target = index + delta;
  if (index < 0 || index >= chain.length || target < 0 || target >= chain.length) {
    return [...chain];
  }
  const next = [...chain];
  const [item] = next.splice(index, 1);
  next.splice(target, 0, item);
  return next;
}

export function addItem(chain: readonly string[], ref: string): string[] {
  const clean = ref.trim();
  if (!REF.test(clean) || chain.includes(clean) || chain.length >= MAX_CHAIN) {
    return [...chain];
  }
  return [...chain, clean];
}

export function setPrimary(chain: readonly string[], ref: string): string[] {
  const clean = ref.trim();
  if (!REF.test(clean)) {
    return [...chain];
  }
  return [clean, ...chain.filter((item) => item !== clean)].slice(0, MAX_CHAIN);
}

export const removeItem = (chain: readonly string[], ref: string): string[] => chain.filter((item) => item !== ref);

export const sameChain = (a: readonly string[], b: readonly string[]): boolean =>
  a.length === b.length && a.every((item, index) => item === b[index]);

export function cloudRef(provider: string, model: string): string | null {
  const ref = `cloud:${provider.trim()}/${model.trim()}`;
  return REF.test(ref) && model.trim() !== '' ? ref : null;
}
