import { sendJson } from '../shared/http';
import { MusicOverview } from './types';

export const setRecognition = (enabled: boolean) => sendJson<MusicOverview>('/api/music', 'PUT', { enabled });
