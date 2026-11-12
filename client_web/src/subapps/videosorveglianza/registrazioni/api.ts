import { adminPath } from '../../../shared/http/basePath';
import { reportError } from '../../../shared/errors/errorBus';
import type { JumpResult, RecordingCamera, SeekResult, SegmentRow, StorageStats, Timeline } from './types';

const CSRF_HEADER = 'X-Nuxiva-Request';
const ID = /^[A-Za-z0-9_-]{1,64}$/;

function safeId(value: string): string {
  if (!ID.test(value)) {
    throw new Error('nvr_invalid_id');
  }
  return value;
}

async function getJson<T>(path: string, params: Record<string, string | number> = {}): Promise<T | null> {
  const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
  const res = await fetch(adminPath(query ? `${path}?${query}` : path), {
    headers: { [CSRF_HEADER]: '1' },
    credentials: 'same-origin',
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`nvr_request_failed_${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchRecordings(): Promise<RecordingCamera[]> {
  try {
    const data = await getJson<{ cameras: RecordingCamera[] }>('/api/nvr/recordings');
    return Array.isArray(data?.cameras) ? data!.cameras.filter((c) => ID.test(c.camera)) : [];
  } catch (cause) {
    reportError('nvr_recordings_error', cause);
    return [];
  }
}

export async function fetchTimeline(camera: string, fromMs: number, toMs: number): Promise<Timeline | null> {
  try {
    return await getJson<Timeline>('/api/nvr/timeline', { camera: safeId(camera), from_ms: Math.floor(fromMs), to_ms: Math.floor(toMs) });
  } catch (cause) {
    reportError('nvr_timeline_error', cause);
    return null;
  }
}

export async function seekTo(camera: string, atMs: number): Promise<SeekResult | null> {
  try {
    return await getJson<SeekResult>('/api/nvr/seek', { camera: safeId(camera), at_ms: Math.max(0, Math.floor(atMs)) });
  } catch (cause) {
    reportError('nvr_seek_error', cause);
    return null;
  }
}

export async function jump(camera: string, atMs: number, direction: 'next' | 'prev', kinds: string[]): Promise<JumpResult | null> {
  try {
    return await getJson<JumpResult>('/api/nvr/jump', {
      camera: safeId(camera),
      at_ms: Math.max(0, Math.floor(atMs)),
      direction,
      kinds: kinds.join(','),
    });
  } catch (cause) {
    reportError('nvr_jump_error', cause);
    return null;
  }
}

export async function nextSegment(camera: string, segment: string): Promise<SegmentRow | null> {
  try {
    return await getJson<SegmentRow>(`/api/nvr/next/${safeId(camera)}/${safeId(segment)}`);
  } catch (cause) {
    reportError('nvr_next_error', cause);
    return null;
  }
}

export async function fetchStorage(): Promise<StorageStats | null> {
  try {
    return await getJson<StorageStats>('/api/nvr/storage');
  } catch (cause) {
    reportError('nvr_storage_error', cause);
    return null;
  }
}

export async function setPinned(camera: string, segment: string, pinned: boolean): Promise<SegmentRow | null> {
  try {
    const res = await fetch(adminPath(`/api/nvr/segments/${safeId(camera)}/${safeId(segment)}/pin`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', [CSRF_HEADER]: '1' },
      credentials: 'same-origin',
      body: JSON.stringify({ pinned }),
    });
    if (!res.ok) {
      throw new Error(`nvr_pin_failed_${res.status}`);
    }
    return (await res.json()) as SegmentRow;
  } catch (cause) {
    reportError('nvr_pin_error', cause);
    return null;
  }
}

export async function deleteSegment(camera: string, segment: string): Promise<boolean> {
  try {
    const res = await fetch(adminPath(`/api/nvr/segments/${safeId(camera)}/${safeId(segment)}`), {
      method: 'DELETE',
      headers: { [CSRF_HEADER]: '1' },
      credentials: 'same-origin',
    });
    if (!res.ok) {
      throw new Error(`nvr_delete_failed_${res.status}`);
    }
    return true;
  } catch (cause) {
    reportError('nvr_delete_error', cause);
    return false;
  }
}

export function playUrl(camera: string, segment: string): string {
  return adminPath(`/api/nvr/play/${safeId(camera)}/${safeId(segment)}`);
}
