import { asRecord, requestJson } from './http';

export const TOKEN_SURFACE = 'token_usage';

export async function fetchTokenWidget(signal?: AbortSignal): Promise<boolean> {
  const settings = asRecord(asRecord(await requestJson<unknown>('/api/system/display-settings', { signal })).settings);
  return asRecord(settings.surfaces)[TOKEN_SURFACE] === true;
}

export async function saveTokenWidget(enabled: boolean): Promise<boolean> {
  const settings = asRecord(
    asRecord(
      await requestJson<unknown>('/api/system/display-settings', {
        method: 'POST',
        body: JSON.stringify({ surfaces: { [TOKEN_SURFACE]: enabled } }),
      }),
    ).settings,
  );
  return asRecord(settings.surfaces)[TOKEN_SURFACE] === true;
}
