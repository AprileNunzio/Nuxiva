import React from 'react';
import { View as AgentsView } from '../core_apps/agents/View';
import { View as AlgorithmsView } from '../core_apps/algorithms/View';
import { View as AutomationsView } from '../core_apps/automations/View';
import { View as BackupView } from '../core_apps/backup/View';
import { View as CamerasView } from '../core_apps/cameras/View';
import { View as EmergencyView } from '../core_apps/emergency/View';
import { View as FeaturesHubView } from '../core_apps/features_hub/View';
import { View as FirewallView } from '../core_apps/firewall/View';
import { View as FlowsView } from '../core_apps/flows/View';
import { View as GoogleView } from '../core_apps/google/View';
import { View as HabitsView } from '../core_apps/habits/View';
import { View as HandsView } from '../core_apps/hands/View';
import { View as HomeAssistantView } from '../apps/home_assistant/View';
import { View as IptvView } from '../apps/iptv/View';
import { View as LawsView } from '../core_apps/laws/View';
import { View as MusicView } from '../apps/music/View';
import { View as NodesView } from '../core_apps/nodes/View';
import { View as OfficeView } from '../core_apps/office/View';
import { View as PeopleView } from '../core_apps/people/View';
import { View as PlacesView } from '../core_apps/places/View';
import { View as StudyView } from '../core_apps/study/View';
import { View as TwinView } from '../core_apps/twin/View';
import { View as UpdaterView } from '../core_apps/updater/View';
import { View as VaultView } from '../core_apps/vault/View';
import { View as VpnView } from '../core_apps/vpn/View';

const CORE_APP_COMPONENTS: Readonly<Record<string, React.FC>> = {
  agents: AgentsView,
  algorithms: AlgorithmsView,
  automations: AutomationsView,
  backup: BackupView,
  cameras: CamerasView,
  emergency: EmergencyView,
  features_hub: FeaturesHubView,
  firewall: FirewallView,
  flows: FlowsView,
  google: GoogleView,
  habits: HabitsView,
  hands: HandsView,
  home_assistant: HomeAssistantView,
  iptv: IptvView,
  laws: LawsView,
  music: MusicView,
  nodes: NodesView,
  office: OfficeView,
  people: PeopleView,
  places: PlacesView,
  study: StudyView,
  twin: TwinView,
  updater: UpdaterView,
  vault: VaultView,
  vpn: VpnView,
};

export function resolveCoreApp(appId: string): React.FC | null {
  return Object.prototype.hasOwnProperty.call(CORE_APP_COMPONENTS, appId) ? CORE_APP_COMPONENTS[appId] : null;
}
