import { sendJson } from '../shared/http';

const BASE = '/api/places';
const enc = encodeURIComponent;

export const addFloor = (name: string, level: number) => sendJson(`${BASE}/floors`, 'POST', { name, level });
export const deleteFloor = (id: string) => sendJson(`${BASE}/floors/${enc(id)}`, 'DELETE');
export const addRoom = (name: string, floorId: string) => sendJson(`${BASE}/rooms`, 'POST', { name, floor_id: floorId });
export const deleteRoom = (id: string) => sendJson(`${BASE}/rooms/${enc(id)}`, 'DELETE');
export const placeDevice = (key: string, roomId: string, senses: readonly string[]) =>
  sendJson(`${BASE}/devices/${key.split('/').map(enc).join('/')}`, 'PUT', { room_id: roomId, senses });
export const importHome = () => sendJson<{ added: number }>(`${BASE}/import`, 'POST');
