import React, { useEffect, useState } from 'react';
import { Copy } from 'lucide-react';
import { PairingPanel } from '../../../node_apps/client_link/components/PairingPanel';
import { reportError } from '../../../shared/errors/errorBus';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { requestJson } from '../../../node_apps/shared/data/http';
import { RequestsPanel } from '../../../node_apps/client_link/components/RequestsPanel';
import { LinksHandle } from '../../../node_apps/client_link/hooks/useLinks';

export const PcLinkPanel: React.FC<{ readonly handle: LinksHandle }> = ({ handle }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [copied, setCopied] = useState(false);
  const [server, setServer] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    requestJson<{ server: string }>('/api/nodes/connection', { signal: controller.signal }).then((result) => setServer(result.server))
      .catch((cause) => !controller.signal.aborted && reportError('nodes_load_failed', cause));
    return () => controller.abort();
  }, []);
  const quote = (value: string) => `'${value.replace(/'/g, `'"'"'`)}'`;
  const command = server ? `curl --fail --show-error --location ${quote(`${server}/nodes/agent.py`)} --output nuxiva-node.py && sudo python3 nuxiva-node.py --server ${quote(server)} --join --install` : '';
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };
  return (
    <div className="min-w-0 space-y-3">
      <h3 className="text-sm font-bold text-slate-950">{t('step2_pc_title')}</h3>
      <p className="text-xs text-slate-600">{t('pc_link_hint')}</p>
      <code className="block overflow-x-auto rounded-xl border border-cyan-300 bg-white p-3 text-xs text-cyan-800">{command}</code>
      <button type="button" disabled={!server} onClick={() => void copy()} className="flex min-h-11 items-center gap-2 rounded-xl border border-cyan-300 px-3 py-2 text-xs text-cyan-900 disabled:opacity-50">
        <Copy className="h-4 w-4" aria-hidden="true" />
        {t(copied ? 'command_copied' : 'copy_command')}
      </button>
      <p className="text-xs text-slate-600">{t('pc_code_hint')}</p>
      <PairingPanel />
      <RequestsPanel handle={handle} />
    </div>
  );
};
