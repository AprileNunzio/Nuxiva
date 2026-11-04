import { asRecord, asString, requestJson } from './http';
import { PROVIDER_ID, list, num } from './parse';
import { Budgets, UsageRow, UsageSummary } from './types';

export const MAX_BUDGET = 1_000_000_000_000;

const cap = (value: unknown): number | null =>
  typeof value === 'number' && Number.isInteger(value) && value > 0 && value <= MAX_BUDGET ? value : null;

function parseRow(value: unknown, key: 'id' | 'ref'): UsageRow | null {
  const row = asRecord(value);
  const id = asString(row[key], 230);
  if (!id) {
    return null;
  }
  return { id, tokensIn: num(row.tokens_in), tokensOut: num(row.tokens_out), calls: num(row.calls), budget: cap(row.budget) };
}

export function parseUsage(value: unknown): UsageSummary {
  const raw = asRecord(value);
  const budgets = asRecord(raw.budgets);
  const providerBudgets: Record<string, number> = {};
  Object.entries(asRecord(budgets.providers)).forEach(([id, amount]) => {
    const parsed = cap(amount);
    if (PROVIDER_ID.test(id) && parsed !== null) {
      providerBudgets[id] = parsed;
    }
  });
  return {
    month: asString(raw.month, 7) ?? '',
    today: num(raw.today),
    total: num(raw.total),
    cloud: num(raw.cloud),
    globalBudget: cap(budgets.global),
    providerBudgets,
    providers: list(raw.providers).map((r) => parseRow(r, 'id')).filter((r): r is UsageRow => r !== null),
    models: list(raw.models).map((r) => parseRow(r, 'ref')).filter((r): r is UsageRow => r !== null),
    days: list(raw.days)
      .map(asRecord)
      .flatMap((d) => {
        const date = asString(d.date, 10);
        return date ? [{ date, tokens: num(d.tokens) }] : [];
      }),
  };
}

export function validateBudgets(budgets: Budgets): Budgets {
  const ok = (value: number | null) => value === null || (Number.isInteger(value) && value > 0 && value <= MAX_BUDGET);
  if (!ok(budgets.global) || !Object.entries(budgets.providers).every(([id, v]) => PROVIDER_ID.test(id) && ok(v))) {
    throw new RangeError('invalid_budget');
  }
  return budgets;
}

export async function fetchUsage(signal?: AbortSignal): Promise<UsageSummary> {
  return parseUsage(await requestJson<unknown>('/api/brains/usage', { signal }));
}

export async function saveBudgets(budgets: Budgets): Promise<UsageSummary> {
  return parseUsage(
    await requestJson<unknown>('/api/brains/usage/budgets', { method: 'PUT', body: JSON.stringify(validateBudgets(budgets)) }),
  );
}
