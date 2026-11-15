import React, { useEffect, useState } from 'react';
import { Box, Check, Copy, Server } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { requestJson } from '../../../node_apps/shared/data/http';

export const DockerGuide: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [serverUrl, setServerUrl] = useState('');
  const [copiedRun, setCopiedRun] = useState(false);
  const [copiedCompose, setCopiedCompose] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    requestJson<{ server: string }>('/api/nodes/connection', { signal: controller.signal })
      .then((result) => setServerUrl(result.server))
      .catch(() => {
        if (typeof window !== 'undefined') {
          setServerUrl(window.location.origin);
        }
      });
    return () => controller.abort();
  }, []);

  const srv = serverUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://192.168.1.100:8080');

  const dockerRunCmd = `docker run -d \\
  --name nuxiva-node \\
  --restart unless-stopped \\
  --net host \\
  -e NUXIVA_SERVER="${srv}" \\
  -e NUXIVA_NAME="satellite-docker" \\
  ghcr.io/aprilenunzio/nuxiva-node:latest`;

  const dockerComposeYaml = `version: '3.8'
services:
  nuxiva-node:
    image: ghcr.io/aprilenunzio/nuxiva-node:latest
    container_name: nuxiva-node
    restart: unless-stopped
    network_mode: host
    environment:
      - NUXIVA_SERVER=${srv}
      - NUXIVA_NAME=satellite-docker`;

  const copy = async (text: string, setCopied: (v: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-on-surface-variant">{t('install_docker_guide')}</p>

      <ol className="flex flex-col gap-2">
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">1</span>
          <span className="min-w-0">{t('install_docker_step_1')}</span>
        </li>
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">2</span>
          <span className="min-w-0">{t('install_docker_step_2')}</span>
        </li>
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">3</span>
          <span className="min-w-0">{t('install_docker_step_3')}</span>
        </li>
      </ol>

      <div className="space-y-4">
        {/* Docker Run Command */}
        <div className="rounded-3xl bg-surface-container p-4">
          <div className="flex items-center justify-between pb-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <Box className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>{t('docker_run_command_title')}</span>
            </h4>
            <button
              type="button"
              onClick={() => void copy(dockerRunCmd, setCopiedRun)}
              className="md-state inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            >
              {copiedRun ? <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
              {t(copiedRun ? 'docker_copied' : 'docker_copy')}
            </button>
          </div>
          <pre className="overflow-x-auto rounded-2xl bg-surface-container-highest p-3 font-mono text-xs text-primary">
            {dockerRunCmd}
          </pre>
        </div>

        {/* Docker Compose YAML */}
        <div className="rounded-3xl bg-surface-container p-4">
          <div className="flex items-center justify-between pb-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <Server className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>{t('docker_compose_title')}</span>
            </h4>
            <button
              type="button"
              onClick={() => void copy(dockerComposeYaml, setCopiedCompose)}
              className="md-state inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            >
              {copiedCompose ? <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
              {t(copiedCompose ? 'docker_copied' : 'docker_copy')}
            </button>
          </div>
          <pre className="overflow-x-auto rounded-2xl bg-surface-container-highest p-3 font-mono text-xs text-primary">
            {dockerComposeYaml}
          </pre>
        </div>
      </div>
    </div>
  );
};
