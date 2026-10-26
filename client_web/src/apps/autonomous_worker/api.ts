import {
  AgentInferenceProfile,
  EpisodicMemory,
  Mission,
  MissionAutomation,
  RuntimeConfig,
  RuntimeHealth,
  WatchdogPayload,
} from './types';

const jsonHeaders = { 'Content-Type': 'application/json' };

export async function fetchMissions(): Promise<Mission[]> {
  const res = await fetch('/api/autonomous/missions');
  if (!res.ok) throw new Error('fetch_missions_failed');
  return res.json();
}

export async function fetchMission(id: string): Promise<Mission> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error('fetch_mission_failed');
  return res.json();
}

export async function createMission(goal: string, directives: string[] = []): Promise<Mission> {
  const res = await fetch('/api/autonomous/missions', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ goal, directives }),
  });
  if (!res.ok) throw new Error('create_mission_failed');
  return res.json();
}

export async function controlMission(id: string, action: string): Promise<Mission> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/control/${encodeURIComponent(action)}`, {
    method: 'POST',
    headers: jsonHeaders,
    body: '{}',
  });
  if (!res.ok) throw new Error('control_mission_failed');
  return res.json();
}

export async function answerQuestion(id: string, qid: string, answer: string, selected: string[]): Promise<Mission> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/answer`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ question_id: qid, answer, selected_options: selected }),
  });
  if (!res.ok) throw new Error('answer_question_failed');
  return res.json();
}

export async function addDirective(id: string, directive: string): Promise<Mission> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(id)}/directives`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ directive }),
  });
  if (!res.ok) throw new Error('add_directive_failed');
  return res.json();
}

export async function fetchRuntimeConfig(): Promise<RuntimeConfig> {
  const res = await fetch('/api/autonomous/runtime/config');
  if (!res.ok) throw new Error('fetch_runtime_config_failed');
  return res.json();
}

export async function updateRuntimeConfig(updates: Partial<RuntimeConfig>): Promise<RuntimeConfig> {
  const res = await fetch('/api/autonomous/runtime/config', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('update_runtime_config_failed');
  return res.json();
}

export async function checkRuntimeHealth(): Promise<RuntimeHealth> {
  const res = await fetch('/api/autonomous/runtime/health', {
    method: 'POST',
    headers: jsonHeaders,
    body: '{}',
  });
  if (!res.ok) throw new Error('check_runtime_health_failed');
  return res.json();
}

export async function fetchAgentProfiles(): Promise<AgentInferenceProfile[]> {
  const res = await fetch('/api/autonomous/runtime/agents');
  if (!res.ok) throw new Error('fetch_agent_profiles_failed');
  return res.json();
}

export async function saveAgentProfile(profile: AgentInferenceProfile): Promise<AgentInferenceProfile> {
  const res = await fetch('/api/autonomous/runtime/agents', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(profile),
  });
  if (!res.ok) throw new Error('save_agent_profile_failed');
  return res.json();
}

export async function deleteAgentProfile(agentId: string): Promise<void> {
  const res = await fetch(`/api/autonomous/runtime/agents/${encodeURIComponent(agentId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('delete_agent_profile_failed');
}

export async function triggerMissionCompression(
  missionId: string
): Promise<{ compressed: boolean; memory: EpisodicMemory }> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(missionId)}/compress`, {
    method: 'POST',
    headers: jsonHeaders,
    body: '{}',
  });
  if (!res.ok) throw new Error('trigger_compression_failed');
  return res.json();
}

export async function fetchMissionAutomations(missionId: string): Promise<MissionAutomation[]> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(missionId)}/automations`);
  if (!res.ok) throw new Error('fetch_mission_automations_failed');
  return res.json();
}

export async function saveMissionWatchdog(
  missionId: string,
  payload: WatchdogPayload
): Promise<MissionAutomation> {
  const res = await fetch(`/api/autonomous/missions/${encodeURIComponent(missionId)}/watchdog`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('save_mission_watchdog_failed');
  return res.json();
}
