/**
 * SMB Shares & Universal File Explorer API Client
 */

export interface SMBFolder {
  readonly kind: string;
  readonly name: string;
  readonly description: string;
  readonly count: number;
  readonly latest: readonly string[];
}

export interface SharesOverviewResponse {
  readonly active: string;
  readonly ip: string;
  readonly windows: string;
  readonly unc: string;
  readonly user: string;
  readonly password?: string;
  readonly folders: readonly SMBFolder[];
  readonly root: string;
}

export interface ShareFileItem {
  readonly name: string;
  readonly is_dir: boolean;
  readonly path: string;
  readonly size: number;
  readonly mtime: number;
  readonly ext: string;
}

export interface ShareFilesResponse {
  readonly folder: string;
  readonly path: string;
  readonly unc: string;
  readonly items: readonly ShareFileItem[];
}

const HEADERS = {
  Accept: 'application/json',
  'X-Nuxiva-Request': '1',
};

export async function fetchSharesOverview(signal?: AbortSignal): Promise<SharesOverviewResponse> {
  const response = await fetch('/api/shares', {
    headers: HEADERS,
    cache: 'no-store',
    signal,
  });
  if (!response.ok) {
    throw new Error(`shares_http_${response.status}`);
  }
  return response.json();
}

export async function fetchShareFiles(subpath: string, signal?: AbortSignal): Promise<ShareFilesResponse> {
  const query = subpath ? `?subpath=${encodeURIComponent(subpath)}` : '';
  const response = await fetch(`/api/shares/files${query}`, {
    headers: HEADERS,
    cache: 'no-store',
    signal,
  });
  if (!response.ok) {
    throw new Error(`files_http_${response.status}`);
  }
  return response.json();
}

export function getFileUrl(path: string): string {
  return `/api/shares/file?path=${encodeURIComponent(path)}`;
}

export async function fetchFileText(path: string, signal?: AbortSignal): Promise<string> {
  const response = await fetch(getFileUrl(path), {
    headers: { 'X-Nuxiva-Request': '1' },
    cache: 'no-store',
    signal,
  });
  if (!response.ok) {
    throw new Error(`file_content_${response.status}`);
  }
  return response.text();
}

export async function createFolder(parent: string, name: string): Promise<{ ok: boolean; name: string; path: string }> {
  const response = await fetch('/api/shares/create_folder', {
    method: 'POST',
    headers: { ...HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ parent, name }),
  });
  if (!response.ok) {
    throw new Error(`create_folder_${response.status}`);
  }
  return response.json();
}

export async function uploadShareFile(subpath: string, file: File): Promise<{ ok: boolean; name: string; path: string; size: number }> {
  const query = `?subpath=${encodeURIComponent(subpath)}&name=${encodeURIComponent(file.name)}`;
  const response = await fetch(`/api/shares/upload${query}`, {
    method: 'PUT',
    headers: {
      'X-Nuxiva-Request': '1',
      'Content-Type': file.type || 'application/octet-stream',
      'Content-Length': String(file.size),
    },
    body: file,
  });
  if (!response.ok) {
    throw new Error(`upload_http_${response.status}`);
  }
  return response.json();
}
