import React, { FormEvent, useState } from 'react';
import { DoorOpen, Download, Layers, MapPin, Plus, Trash2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, Field, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { addFloor, addRoom, deleteFloor, deleteRoom, importHome, placeDevice } from './api';
import { PlacesOverview } from './types';

const SENSES = ['sees', 'hears', 'shows', 'speaks'] as const;

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/places');
  const { data, error, loading, reload } = useResource<PlacesOverview>('/api/places', 15000);
  const { busy, run } = useAction(reload);
  const [floorName, setFloorName] = useState('');
  const [level, setLevel] = useState(0);
  const [roomName, setRoomName] = useState('');
  const [roomFloor, setRoomFloor] = useState('');
  const [note, setNote] = useState('');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const floorName_ = (id: string) => data.floors.find((floor) => floor.id === id)?.name ?? t('no_floor');

  const submitFloor = async (event: FormEvent) => {
    event.preventDefault();
    if (floorName.trim() && (await run(() => addFloor(floorName.trim(), level), 'places_floor_failed')) !== null) {
      setFloorName('');
    }
  };

  const submitRoom = async (event: FormEvent) => {
    event.preventDefault();
    if (roomName.trim() && (await run(() => addRoom(roomName.trim(), roomFloor), 'places_room_failed')) !== null) {
      setRoomName('');
    }
  };

  const toggleSense = (key: string, roomId: string, current: readonly string[], sense: string) => {
    const next = current.includes(sense) ? current.filter((item) => item !== sense) : [...current, sense];
    void run(() => placeDevice(key, roomId, next), 'places_place_failed');
  };

  const importAreas = async () => {
    const out = await run(importHome, 'places_import_failed');
    setNote(out ? t('imported', { n: out.added }) : '');
  };

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reload}
      actions={
        <Btn busy={busy} onClick={() => void importAreas()}>
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          {t('import_ha')}
        </Btn>
      }
    >
      <StatRow>
        <Stat label={t('stat_floors')} value={data.floors.length} />
        <Stat label={t('stat_rooms')} value={data.rooms.length} tone="emerald" />
        <Stat label={t('stat_devices')} value={data.devices.length} tone="amber" />
        <Stat label={t('stat_people')} value={data.people.length} tone="purple" />
      </StatRow>
      {note ? <Pill tone="emerald">{note}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('floors_title')} icon={<Layers className="h-4 w-4 text-cyan-700" aria-hidden="true" />}>
          {data.floors.length === 0 ? (
            <Empty>{t('floors_empty')}</Empty>
          ) : (
            <List>
              {data.floors.map((floor) => (
                <Row key={floor.id} actions={<Btn tone="rose" busy={busy} onClick={() => void run(() => deleteFloor(floor.id), 'places_floor_failed')} title={t('delete')}><Trash2 className="h-3.5 w-3.5" aria-hidden="true" /></Btn>}>
                  <b>{floor.name}</b>
                  <span className="ml-2 text-xs text-slate-500">{t('level', { n: floor.level })}</span>
                </Row>
              ))}
            </List>
          )}
          <form onSubmit={submitFloor} className="mt-3 flex flex-wrap gap-2">
            <input className={`${inputClass} flex-1`} value={floorName} maxLength={40} onChange={(event) => setFloorName(event.target.value)} placeholder={t('floor_name')} aria-label={t('floor_name')} />
            <input className={`${inputClass} w-20`} type="number" min={-5} max={50} value={level} onChange={(event) => setLevel(Number(event.target.value))} aria-label={t('level_label')} />
            <Btn type="submit" busy={busy}><Plus className="h-3.5 w-3.5" aria-hidden="true" />{t('add')}</Btn>
          </form>
        </Panel>
        <Panel title={t('rooms_title')} icon={<DoorOpen className="h-4 w-4 text-emerald-700" aria-hidden="true" />}>
          {data.rooms.length === 0 ? (
            <Empty>{t('rooms_empty')}</Empty>
          ) : (
            <List>
              {data.rooms.map((room) => (
                <Row key={room.id} actions={<Btn tone="rose" busy={busy} onClick={() => void run(() => deleteRoom(room.id), 'places_room_failed')} title={t('delete')}><Trash2 className="h-3.5 w-3.5" aria-hidden="true" /></Btn>}>
                  <b>{room.name}</b>
                  <span className="ml-2 text-xs text-slate-500">{floorName_(room.floor_id)}</span>
                  {room.ha_area ? <Pill tone="cyan">{room.ha_area}</Pill> : null}
                </Row>
              ))}
            </List>
          )}
          <form onSubmit={submitRoom} className="mt-3 flex flex-wrap gap-2">
            <input className={`${inputClass} flex-1`} value={roomName} maxLength={40} onChange={(event) => setRoomName(event.target.value)} placeholder={t('room_name')} aria-label={t('room_name')} />
            <select className={`${inputClass} w-40`} value={roomFloor} onChange={(event) => setRoomFloor(event.target.value)} aria-label={t('floor')}>
              <option value="">{t('no_floor')}</option>
              {data.floors.map((floor) => (
                <option key={floor.id} value={floor.id}>{floor.name}</option>
              ))}
            </select>
            <Btn type="submit" busy={busy}><Plus className="h-3.5 w-3.5" aria-hidden="true" />{t('add')}</Btn>
          </form>
        </Panel>
      </div>
      <Panel title={t('devices_title')} icon={<MapPin className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
        {data.devices.length === 0 ? (
          <Empty>{t('devices_empty')}</Empty>
        ) : (
          <List>
            {data.devices.map((device) => (
              <Row key={device.key}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <b>{device.name}</b>
                    <span className="ml-2 text-[11px] text-slate-500">{device.kind}{device.hint ? ` · ${device.hint}` : ''}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      className={`${inputClass} w-44`}
                      value={device.room_id}
                      disabled={busy}
                      aria-label={t('room')}
                      onChange={(event) => void run(() => placeDevice(device.key, event.target.value, device.senses), 'places_place_failed')}
                    >
                      <option value="">{t('unplaced')}</option>
                      {data.rooms.map((room) => (
                        <option key={room.id} value={room.id}>{room.name}</option>
                      ))}
                    </select>
                    {device.room_id
                      ? SENSES.map((sense) => {
                          const placement = data.placements.find((item) => item.key === device.key);
                          const current = placement?.senses ?? [];
                          return (
                            <Btn key={sense} tone={current.includes(sense) ? 'emerald' : 'slate'} busy={busy} onClick={() => toggleSense(device.key, device.room_id, current, sense)}>
                              {t(`sense_${sense}`)}
                            </Btn>
                          );
                        })
                      : null}
                  </div>
                </div>
              </Row>
            ))}
          </List>
        )}
      </Panel>
      {data.people.length > 0 ? (
        <Panel title={t('people_title')}>
          <div className="flex flex-wrap gap-2">
            {data.people.map((person) => (
              <Pill key={person.slug} tone="purple">{person.name}</Pill>
            ))}
          </div>
        </Panel>
      ) : null}
    </AppFrame>
  );
};

export default View;
