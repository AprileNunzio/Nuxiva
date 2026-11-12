import { sendJson } from '../shared/http';
import { GestureProfile, HandsView } from './types';

export { saveSettings as saveHandsSettings, setMode as setHandsMode } from '../shared/featureApi';

export const HANDS_PROFILE_URL = '/api/hands/profile';

export const saveProfile = (profile: GestureProfile) => sendJson<HandsView>(HANDS_PROFILE_URL, 'PUT', profile);

export const resetProfile = () => sendJson<HandsView>(`${HANDS_PROFILE_URL}/reset`, 'POST');
