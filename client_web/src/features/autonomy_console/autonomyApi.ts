import { AutonomyCognitionSnapshot } from './types';

function sanitizeToken(value: string): string {
  return value.replace(/[\u0000-\u001F\u007F\u202E<>]/g, '').trim().slice(0, 300);
}

export async function fetchAutonomySnapshot(
  endpoint = '/api/v1/agency/autonomy/snapshot'
): Promise<AutonomyCognitionSnapshot> {
  const response = await fetch(endpoint, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw new Error(`autonomy_snapshot_http_${response.status}`);
  }
  return (await response.json()) as AutonomyCognitionSnapshot;
}

export async function submitEpistemicDecision(
  questionId: string,
  optionKey: string,
  endpoint = '/api/v1/agency/autonomy/answer'
): Promise<{ ok: boolean }> {
  const cleanId = sanitizeToken(questionId);
  const cleanOption = sanitizeToken(optionKey);
  if (!cleanId || !cleanOption) {
    throw new Error('autonomy_invalid_decision_payload');
  }
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ question_id: cleanId, option_key: cleanOption }),
  });
  if (!response.ok) {
    throw new Error(`autonomy_decision_http_${response.status}`);
  }
  return (await response.json()) as { ok: boolean };
}
