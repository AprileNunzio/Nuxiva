import { PkiGenerateOptions, PkiStatus } from './types';

export async function fetchPkiStatus(): Promise<PkiStatus> {
  const res = await fetch('/api/secure/pki/status');
  if (!res.ok) {
    throw new Error(`Failed to fetch PKI status: ${res.status}`);
  }
  return res.json();
}

export async function generateEnterpriseCertificate(
  options: PkiGenerateOptions
): Promise<PkiStatus> {
  const res = await fetch('/api/secure/pki/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Nuxiva-Request': '1',
    },
    body: JSON.stringify(options),
  });
  if (!res.ok) {
    throw new Error(`Failed to generate certificate: ${res.status}`);
  }
  return fetchPkiStatus();
}

export async function downloadClientBundle(
  identity: string,
  password?: string
): Promise<void> {
  const res = await fetch('/api/secure/pki/client-bundle', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Nuxiva-Request': '1',
    },
    body: JSON.stringify({ identity, password }),
  });
  if (!res.ok) {
    throw new Error(`Failed to generate client bundle: ${res.status}`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${identity || 'client-bundle'}.p12`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
