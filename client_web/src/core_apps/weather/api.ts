import { NodeModuleError } from '../../node_apps/shared/data/http';
import { asList, asObject, num, sendJson, text, getJson, flag } from '../shared/http';
import { Preview, PreviewDay, SearchHit, WeatherOverview, WeatherPlace, WeatherUnits } from './types';

const BASE = '/api/weather';
const ID = /^[0-9a-f]{8}$/;
const WIND_UNITS: readonly WeatherUnits['wind'][] = ['kmh', 'ms', 'mph', 'kn'];
const ERRORS: readonly WeatherOverview['error'][] = ['', 'no_location', 'unavailable'];

export const overviewUrl = (place: string): string => (ID.test(place) ? `${BASE}/overview?place=${place}` : `${BASE}/overview`);

const place = (raw: unknown): WeatherPlace | null => {
  const row = asObject(raw);
  const id = text(row.id);
  const name = text(row.name);
  return ID.test(id) && name ? { id, name, detail: text(row.detail), lat: num(row.lat), lon: num(row.lon) } : null;
};

const units = (raw: unknown): WeatherUnits => {
  const row = asObject(raw);
  const wind = text(row.wind) as WeatherUnits['wind'];
  return {
    temp: row.temp === 'f' ? 'f' : 'c',
    wind: WIND_UNITS.includes(wind) ? wind : 'kmh',
    precip: row.precip === 'in' ? 'in' : 'mm',
    pressure: row.pressure === 'inhg' ? 'inhg' : 'hpa',
  };
};

const day = (raw: unknown): PreviewDay => {
  const row = asObject(raw);
  return { label: text(row.label), tmax: num(row.tmax), tmin: num(row.tmin), rain: num(row.rain), wind: num(row.wind) };
};

const preview = (raw: unknown): Preview | null => {
  const body = asObject(raw);
  const now = asObject(body.current);
  if (Object.keys(now).length === 0) return null;
  const air = asObject(body.air);
  return {
    location: text(body.location),
    desc: text(now.desc),
    temp: num(now.temp),
    feels: num(now.feels),
    humidity: num(now.humidity),
    wind: num(now.wind),
    gust: num(now.gust),
    dirName: text(now.dir_name),
    pressure: num(now.pressure),
    uv: num(now.uv),
    aqi: typeof air.aqi === 'number' ? air.aqi : null,
    aqiLevel: text(air.level),
    stale: flag(body.stale),
    units: units(body.units),
    days: asList(body.days).slice(0, 7).map(day),
  };
};

export const parseOverview = (raw: unknown): WeatherOverview => {
  const body = asObject(raw);
  const error = text(body.error) as WeatherOverview['error'];
  const defaultId = text(body.default);
  return {
    places: asList(body.places).map(place).filter((item): item is WeatherPlace => item !== null),
    defaultId: ID.test(defaultId) ? defaultId : '',
    error: ERRORS.includes(error) ? error : '',
    preview: preview(body.report),
  };
};

export const searchPlaces = async (query: string): Promise<SearchHit[]> => {
  const body = asObject(await getJson(`${BASE}/search?q=${encodeURIComponent(query.trim().slice(0, 80))}`));
  return asList(body.items).flatMap((raw) => {
    const row = asObject(raw);
    const name = text(row.name);
    return name && typeof row.lat === 'number' && typeof row.lon === 'number' ? [{ name, detail: text(row.detail), lat: row.lat, lon: row.lon }] : [];
  });
};

export const addPlace = async (hit: SearchHit, makeDefault: boolean): Promise<void> => {
  await sendJson(`${BASE}/places`, 'POST', { name: hit.name, detail: hit.detail, lat: hit.lat, lon: hit.lon, default: makeDefault });
};

const guarded = (id: string): string => {
  if (!ID.test(id)) throw new NodeModuleError('place_unknown', 404);
  return id;
};

export const setDefault = async (id: string): Promise<void> => {
  await sendJson(`${BASE}/places/${guarded(id)}/default`, 'POST');
};

export const renamePlace = async (id: string, name: string): Promise<void> => {
  await sendJson(`${BASE}/places/${guarded(id)}`, 'PATCH', { name: name.trim().slice(0, 80) });
};

export const deletePlace = async (id: string): Promise<void> => {
  await sendJson(`${BASE}/places/${guarded(id)}`, 'DELETE');
};
