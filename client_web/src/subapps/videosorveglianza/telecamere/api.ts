import { adminPath } from '../../../shared/http/basePath';
import { reportError } from '../../../shared/errors/errorBus';
import type { CameraDraft, CameraRow, CamerasOverview, CameraSource } from './types';

const CSRF_HEADER = 'X-Nuxiva-Request';

function sanitizeDraft(draft: CameraDraft): CameraDraft {
  const name = draft.name.trim().slice(0, 60);
  const kind = draft.kind.trim().toLowerCase();
  let url = draft.url.trim();
  if (kind === 'webcam' && !url) {
    url = '0';
  }
  return {
    name,
    kind,
    url,
    retention_min: Number(draft.retention_min) || 5,
  };
}

export async function fetchCameras(): Promise<CamerasOverview> {
  try {
    const res = await fetch(adminPath('/api/cameras'), {
      headers: { [CSRF_HEADER]: '1' },
    });
    if (!res.ok) {
      throw new Error(`cameras_fetch_failed_${res.status}`);
    }
    const data = await res.json();
    return {
      cameras: Array.isArray(data.cameras) ? data.cameras : [],
      kinds: Array.isArray(data.kinds) ? data.kinds : ['webcam', 'rtsp', 'rtsps', 'onvif', 'hikvision'],
      retentions: Array.isArray(data.retentions) ? data.retentions : [5, 15, 60],
    };
  } catch (cause) {
    reportError('cameras_fetch_error', cause);
    return {
      cameras: [],
      kinds: ['webcam', 'rtsp', 'rtsps', 'onvif', 'hikvision'],
      retentions: [5, 15, 60],
    };
  }
}

export async function fetchSources(): Promise<CameraSource[]> {
  try {
    const res = await fetch(adminPath('/api/cameras/sources'), {
      headers: { [CSRF_HEADER]: '1' },
    });
    if (!res.ok) {
      throw new Error(`sources_fetch_failed_${res.status}`);
    }
    const data = await res.json();
    return Array.isArray(data.sources) ? data.sources : [];
  } catch (cause) {
    reportError('cameras_sources_error', cause);
    return [];
  }
}

export async function addCamera(draft: CameraDraft): Promise<CameraRow | null> {
  const payload = sanitizeDraft(draft);
  if (!payload.name) {
    reportError('cameras_add_empty_name', new Error('Empty camera name'));
    return null;
  }
  try {
    const res = await fetch(adminPath('/api/cameras'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        [CSRF_HEADER]: '1',
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`cameras_add_failed_${res.status}_${err}`);
    }
    return await res.json();
  } catch (cause) {
    reportError('cameras_add_error', cause);
    return null;
  }
}

export async function patchCamera(id: string, change: Partial<CameraRow>): Promise<CameraRow | null> {
  try {
    const res = await fetch(adminPath(`/api/cameras/${encodeURIComponent(id)}`), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        [CSRF_HEADER]: '1',
      },
      body: JSON.stringify(change),
    });
    if (!res.ok) {
      throw new Error(`cameras_patch_failed_${res.status}`);
    }
    return await res.json();
  } catch (cause) {
    reportError('cameras_patch_error', cause);
    return null;
  }
}

export async function deleteCamera(id: string): Promise<boolean> {
  try {
    const res = await fetch(adminPath(`/api/cameras/${encodeURIComponent(id)}`), {
      method: 'DELETE',
      headers: { [CSRF_HEADER]: '1' },
    });
    if (!res.ok) {
      throw new Error(`cameras_delete_failed_${res.status}`);
    }
    return true;
  } catch (cause) {
    reportError('cameras_delete_error', cause);
    return false;
  }
}
