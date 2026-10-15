import React, { useState } from 'react';
import { Download, Fingerprint, Power, RotateCw, ScanLine } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { ControlScope, DESTRUCTIVE_COMMANDS, KNOWN_COMMANDS, NodeCommand, sendNodeCommand } from '../data/nodeConsoleApi';
import { CONSOLE_SCOPE } from '../scope';

const ICONS: Readonly<Record<NodeCommand, typeof Power>> = {
  identify: Fingerprint,
  adapt: ScanLine,
  update: Download,
  restart: RotateCw,
  reboot: Power,
};

interface NodeCommandBarProps {
  readonly nodeId: string;
  readonly nodeName: string;
  readonly scope: ControlScope;
  readonly commands: readonly NodeCommand[];
}

type Feedback = { readonly command: NodeCommand; readonly outcome: 'executing' | 'queued' | 'failed' };

export const NodeCommandBar: React.FC<NodeCommandBarProps> = ({ nodeId, nodeName, scope, commands }) => {
  const { t } = useScopedI18n(CONSOLE_SCOPE);
  const [pending, setPending] = useState<NodeCommand | null>(null);
  const [confirming, setConfirming] = useState<NodeCommand | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const run = async (command: NodeCommand) => {
    setPending(command);
    setFeedback(null);
    try {
      setFeedback({ command, outcome: await sendNodeCommand(nodeId, command) });
    } catch (cause) {
      reportError('node_command_failed', cause);
      setFeedback({ command, outcome: 'failed' });
    } finally {
      setPending(null);
      setConfirming(null);
    }
  };

  const request = (command: NodeCommand) => (DESTRUCTIVE_COMMANDS.has(command) ? setConfirming(command) : run(command));
  const available = KNOWN_COMMANDS.filter((command) => commands.includes(command));

  if (available.length === 0) {
    return <p className="text-xs text-slate-500">{t(scope === 'mesh' ? 'commands_unpaired' : 'commands_none')}</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {available.map((command) => {
          const Icon = ICONS[command];
          const danger = command === 'reboot';
          return (
            <button
              key={command}
              type="button"
              onClick={() => request(command)}
              disabled={pending !== null}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 ${
                danger
                  ? 'border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20 focus-visible:ring-rose-300'
                  : 'border-slate-700 bg-slate-900/70 text-slate-200 hover:border-cyan-400/60 hover:text-white focus-visible:ring-cyan-400'
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${pending === command ? 'animate-spin' : ''}`} aria-hidden="true" />
              {t(`command_${command}`)}
            </button>
          );
        })}
      </div>
      {feedback && (
        <p
          role="status"
          className={`text-xs ${feedback.outcome === 'failed' ? 'text-rose-300' : 'text-emerald-300'}`}
        >
          {t(`feedback_${feedback.outcome}`, { command: t(`command_${feedback.command}`) })}
        </p>
      )}
      {confirming && (
        <ConfirmDialog
          title={t(`confirm_${confirming}_title`, { name: nodeName })}
          body={t(scope === 'local' ? `confirm_${confirming}_local` : `confirm_${confirming}_remote`, { name: nodeName })}
          confirmLabel={t(`command_${confirming}`)}
          cancelLabel={t('cancel')}
          pending={pending !== null}
          tone={confirming === 'reboot' ? 'danger' : 'neutral'}
          onConfirm={() => run(confirming)}
          onCancel={() => setConfirming(null)}
        />
      )}
    </div>
  );
};
