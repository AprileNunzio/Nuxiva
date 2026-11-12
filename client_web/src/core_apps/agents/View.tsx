import { PAGE_CLASS } from '../../shared/ui/layout';
import React, { useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { setAgentMode } from './data/teamApi';
import { useTeam } from './hooks/useTeam';
import { ActivityFeed } from './components/ActivityFeed';
import { AgentDetail } from './components/AgentDetail';
import { AgentList, isOperative } from './components/AgentList';
import { CreateAgentDialog } from './components/CreateAgentDialog';
import { CreateKind, TeamHeader } from './components/TeamHeader';
import { ExpertsSection } from './experts/ExpertsSection';
import { panelClass, useAgentsI18n } from './scope';

export const View: React.FC = () => {
  const { t } = useAgentsI18n();
  const handle = useTeam();
  const { team } = handle;
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState<CreateKind | null>(null);
  const toolCount = useMemo(() => {
    const counts: Record<string, number> = {};
    team?.tools.forEach((tool) => {
      counts[tool.owner] = (counts[tool.owner] ?? 0) + 1;
    });
    return counts;
  }, [team]);

  if (!team) {
    return (
      <div className={PAGE_CLASS}>
        <ExpertsSection />
        <div className="flex min-h-[20vh] items-center justify-center gap-2 text-sm text-slate-600" role="status">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-700" aria-hidden="true" />
          {t('loading')}
        </div>
      </div>
    );
  }

  const members = team.agents.filter(isOperative);
  const agent = members.find((a) => a.id === selected) ?? members[0] ?? null;

  return (
    <div className={PAGE_CLASS}>
      <ExpertsSection />
      <TeamHeader
        team={team}
        busy={handle.busy !== null}
        onCreate={setCreating}
        onAutonomy={(enabled) => void handle.run('autonomy', () => setAgentMode('forge', enabled ? '1' : '0'), 'team_mode_failed')}
      />
      <div className="grid gap-4 lg:grid-cols-[20rem_minmax(0,1fr)] 3xl:grid-cols-[22rem_minmax(0,1fr)_26rem]">
        <aside className={panelClass} aria-label={t('team_list')}>
          <AgentList agents={members} selected={agent?.id ?? null} toolCount={toolCount} onSelect={setSelected} />
        </aside>
        <div className="flex min-w-0 flex-col gap-4">
          {agent && <AgentDetail key={agent.id} agent={agent} team={team} handle={handle} onDeleted={() => setSelected(null)} />}
          <div className="3xl:hidden">
            <ActivityFeed messages={team.messages} agents={members} />
          </div>
        </div>
        <div className="hidden min-w-0 3xl:block">
          <ActivityFeed messages={team.messages} agents={members} />
        </div>
      </div>
      {creating === 'agent' && (
        <CreateAgentDialog
          handle={handle}
          onClose={(id) => {
            setCreating(null);
            if (id) {
              setSelected(id);
            }
          }}
        />
      )}
    </div>
  );
};

export default View;
