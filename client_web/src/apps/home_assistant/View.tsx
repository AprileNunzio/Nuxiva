import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import {
  AppFrame,
  Panel,
  Stat,
  StatRow,
  Pill,
  Btn,
  Row,
  List,
  Empty,
  Loading,
  inputClass,
} from '../shared/kit';
import {
  getOverview,
  getEntities,
  getRooms,
  getEnergy,
  getAutomations,
  toggleAutomation,
  runAutomation,
  controlDevice,
  askAssist,
  syncHome,
  importPlaces,
} from './api';
import { ConnectionPanel } from './components/ConnectionPanel';
import type {
  Entity,
  Area,
  Floor,
  RoomItem,
  AutomationItem,
  EnergyData,
  HomeOverview,
} from './types';
import {
  Home,
  Zap,
  Sliders,
  Play,
  RefreshCw,
  Search,
  Settings,
  Layers,
  MessageSquare,
  Thermometer,
  Droplets,
  ExternalLink,
  Power,
  Eye,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

type Tab = 'devices' | 'rooms' | 'automations' | 'scenes' | 'energy' | 'assist' | 'settings';

export function View() {
  const { openApp } = useOSApp();
  const { t, lang } = useScopedI18n('apps/home_assistant');

  const [tab, setTab] = useState<Tab>('devices');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [actionMsg, setActionMsg] = useState('');

  // Data states
  const [overview, setOverview] = useState<HomeOverview | null>(null);
  const [entities, setEntities] = useState<readonly Entity[]>([]);
  const [areas, setAreas] = useState<readonly Area[]>([]);
  const [floors, setFloors] = useState<readonly Floor[]>([]);
  const [rooms, setRooms] = useState<readonly RoomItem[]>([]);
  const [automations, setAutomations] = useState<readonly AutomationItem[]>([]);
  const [energy, setEnergy] = useState<EnergyData | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [domainFilter, setDomainFilter] = useState('all');
  const [roomFilter, setRoomFilter] = useState('all');

  // Assist test state
  const [assistQuery, setAssistQuery] = useState('');
  const [assistResult, setAssistResult] = useState<{ speech: string; source?: string; ok: boolean } | null>(null);
  const [assistBusy, setAssistBusy] = useState(false);

  // Load all home data
  useEffect(() => {
    if (overview?.status === 'not_configured') setTab('settings');
  }, [overview?.status]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, ent, rm, aut, en] = await Promise.all([
        getOverview().catch(() => null),
        getEntities().catch(() => ({ entities: [], areas: [], floors: [], services: {} })),
        getRooms().catch(() => ({ rooms: [] })),
        getAutomations().catch(() => ({ automations: [] })),
        getEnergy().catch(() => null),
      ]);
      setOverview(ov);
      setEntities(ent.entities || []);
      setAreas(ent.areas || []);
      setFloors(ent.floors || []);
      setRooms(rm.rooms || []);
      setAutomations(aut.automations || []);
      setEnergy(en);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
    const timer = setInterval(() => {
      void getOverview().then(setOverview).catch(() => {});
      void getEnergy().then(setEnergy).catch(() => {});
    }, 15000);
    return () => clearInterval(timer);
  }, [loadData]);

  // Synchronize Home Assistant
  const handleSync = async () => {
    setBusy(true);
    try {
      const updated = await syncHome();
      setOverview(updated);
      await loadData();
      setActionMsg(t('sync_now') + ' ✓');
      setTimeout(() => setActionMsg(''), 4000);
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : 'Errore');
    } finally {
      setBusy(false);
    }
  };

  // Synchronize Places with HA Areas
  const handleSyncPlaces = async () => {
    setBusy(true);
    try {
      const res = await importPlaces();
      setActionMsg(`${t('places_synced')} (${res.added} aree)`);
      await loadData();
      setTimeout(() => setActionMsg(''), 4000);
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : 'Errore');
    } finally {
      setBusy(false);
    }
  };

  // Toggle or run automation
  const handleToggleAuto = async (auto: AutomationItem) => {
    const nextOn = auto.state !== 'on';
    setBusy(true);
    try {
      await toggleAutomation(auto.entity_id, nextOn);
      setAutomations((prev) =>
        prev.map((a) => (a.entity_id === auto.entity_id ? { ...a, state: nextOn ? 'on' : 'off' } : a))
      );
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : 'Errore');
    } finally {
      setBusy(false);
    }
  };

  const handleRunAuto = async (auto: AutomationItem) => {
    setBusy(true);
    try {
      await runAutomation(auto.entity_id);
      setActionMsg(`${auto.alias}: ${t('run_now')} ✓`);
      setTimeout(() => setActionMsg(''), 3000);
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : 'Errore');
    } finally {
      setBusy(false);
    }
  };

  // Device control (on/off, climate, covers)
  const handleControl = async (entityId: string, service: string, data?: Record<string, unknown>) => {
    setBusy(true);
    try {
      const res = await controlDevice(entityId, service, data);
      if (res.ok && res.state) {
        setEntities((prev) =>
          prev.map((e) => (e.entity_id === entityId ? { ...e, state: res.state! } : e))
        );
      }
    } catch (err: unknown) {
      setActionMsg(err instanceof Error ? err.message : 'Errore');
    } finally {
      setBusy(false);
    }
  };

  // Run Assist prompt
  const handleAskAssist = async (textToRun?: string) => {
    const q = textToRun || assistQuery;
    if (!q.trim()) return;
    setAssistBusy(true);
    setAssistResult(null);
    try {
      const res = await askAssist(q.trim(), lang);
      setAssistResult({
        speech: res.speech || (res.ok ? 'Eseguito da Home Assistant' : 'Nessuna risposta da Assist'),
        source: res.source,
        ok: res.ok,
      });
    } catch (err: unknown) {
      setAssistResult({
        speech: err instanceof Error ? err.message : 'Errore comunicazione Assist',
        ok: false,
      });
    } finally {
      setAssistBusy(false);
    }
  };

  // Filtered entities for devices tab
  const filteredEntities = useMemo(() => {
    return entities.filter((e) => {
      if (domainFilter !== 'all' && e.domain !== domainFilter) return false;
      if (roomFilter !== 'all' && e.area_id !== roomFilter) return false;
      if (search.trim()) {
        const s = search.toLowerCase();
        const matchName = e.name.toLowerCase().includes(s);
        const matchId = e.entity_id.toLowerCase().includes(s);
        if (!matchName && !matchId) return false;
      }
      return true;
    });
  }, [entities, domainFilter, roomFilter, search]);

  // Scene entities
  const sceneEntities = useMemo(() => {
    return entities.filter((e) => e.domain === 'scene');
  }, [entities]);

  // Area map for fast room name lookup
  const areaNameMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const a of areas) m.set(a.area_id, a.name);
    return m;
  }, [areas]);

  if (loading && !overview) {
    return <Loading label="Caricamento Home Assistant…" />;
  }

  const isOnline = overview?.status === 'online';

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={loadData}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={isOnline ? 'emerald' : 'rose'}>
            {isOnline ? t('status_online') : t('status_offline')}
          </Pill>
          <Btn
            tone="cyan"
            busy={busy}
            onClick={handleSync}
            title={t('sync_now')}
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">{t('sync_now')}</span>
          </Btn>
          <Btn
            tone="slate"
            onClick={() => openApp?.({ appId: 'places' })}
            title={t('open_places_app')}
          >
            <Layers className="h-3.5 w-3.5 text-cyan-700" aria-hidden="true" />
            <span className="hidden md:inline">{t('open_places_app')}</span>
          </Btn>
        </div>
      }
    >
      {/* Action feedback message */}
      {actionMsg ? (
        <div className="mb-4 rounded-xl border border-cyan-500/40 bg-cyan-950/60 px-4 py-2 text-xs font-semibold text-cyan-800">
          {actionMsg}
        </div>
      ) : null}

      {/* Top summary stats */}
      <StatRow>
        <Stat
          label={t('instant_power')}
          value={`${energy?.summary.total_power_w ?? '—'} W`}
          tone="amber"
        />
        <Stat
          label={t('solar_power')}
          value={`${energy?.summary.total_solar_w ?? '—'} W`}
          tone="emerald"
        />
        <Stat
          label={t('net_power')}
          value={`${energy?.summary.net_power_w ?? '—'} W`}
          tone="cyan"
        />
        <Stat
          label={t('total_devices')}
          value={overview?.devices_count ?? 0}
          tone="slate"
        />
        <Stat
          label={t('total_entities')}
          value={overview?.entities_count ?? entities.length}
          tone="purple"
        />
        <Stat
          label={t('ha_version')}
          value={overview?.ha_version || '—'}
          tone="slate"
        />
      </StatRow>

      {/* Navigation tabs */}
      <div className="my-4 flex flex-wrap gap-1.5 border-b border-slate-200 pb-2">
        {(
          [
            ['devices', t('tab_devices'), Sliders],
            ['rooms', t('tab_rooms'), Home],
            ['automations', t('tab_automations'), Play],
            ['scenes', t('tab_scenes'), Layers],
            ['energy', t('tab_energy'), Zap],
            ['assist', t('tab_assist'), MessageSquare],
            ['settings', t('tab_settings'), Settings],
          ] as const
        ).map(([tabKey, label, IconComponent]) => (
          <button
            key={tabKey}
            type="button"
            onClick={() => setTab(tabKey)}
            className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              tab === tabKey
                ? 'bg-cyan-500/20 text-cyan-700 ring-1 ring-cyan-500/40'
                : 'text-slate-500 hover:bg-slate-100/60 hover:text-slate-800'
            }`}
          >
            <IconComponent className="h-4 w-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      {/* TAB 1: DEVICES */}
      {tab === 'devices' ? (
        <div className="space-y-4">
          {/* Controls & Filter Bar */}
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-3">
            <div className="relative min-w-[200px] flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" aria-hidden="true" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('search_placeholder')}
                className={`${inputClass} pl-9`}
              />
            </div>
            <select
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800"
            >
              <option value="all">{t('filter_domain_all')}</option>
              <option value="light">{t('filter_domain_light')}</option>
              <option value="switch">{t('filter_domain_switch')}</option>
              <option value="climate">{t('filter_domain_climate')}</option>
              <option value="cover">{t('filter_domain_cover')}</option>
              <option value="sensor">{t('filter_domain_sensor')}</option>
              <option value="media_player">{t('filter_domain_media_player')}</option>
            </select>
            <select
              value={roomFilter}
              onChange={(e) => setRoomFilter(e.target.value)}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800"
            >
              <option value="all">{t('filter_room_all')}</option>
              {areas.map((a) => (
                <option key={a.area_id} value={a.area_id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Device Cards Grid */}
          {filteredEntities.length === 0 ? (
            <Empty>{t('no_devices')}</Empty>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredEntities.map((entity) => {
                const isOn = entity.state === 'on';
                const isControllable = entity.controllable;
                const areaName = entity.area_id ? areaNameMap.get(entity.area_id) || entity.area_id : '';

                return (
                  <div
                    key={entity.entity_id}
                    className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-gradient-to-br from-white/80 to-slate-50 p-4 shadow-sm"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <h3 className="truncate text-sm font-bold text-slate-900" title={entity.name}>
                            {entity.name}
                          </h3>
                          <p className="truncate font-mono text-[11px] text-slate-500" title={entity.entity_id}>
                            {entity.entity_id}
                          </p>
                        </div>
                        <Pill
                          tone={
                            isOn
                              ? 'emerald'
                              : entity.state === 'unavailable'
                              ? 'rose'
                              : 'slate'
                          }
                        >
                          {entity.state}
                        </Pill>
                      </div>

                      {areaName ? (
                        <div className="mt-2 inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50/80 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                          <Home className="h-3 w-3 text-cyan-600" aria-hidden="true" />
                          {areaName}
                        </div>
                      ) : null}

                      {/* Attributes preview */}
                      <div className="mt-2 space-y-1 text-[11px] text-slate-500">
                        {entity.attrs.temperature !== undefined ? (
                          <div className="flex items-center gap-1">
                            <Thermometer className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
                            <span>{String(entity.attrs.temperature)} °C</span>
                          </div>
                        ) : null}
                        {entity.attrs.brightness !== undefined ? (
                          <div className="flex items-center gap-1">
                            <span>Luminosità: {Math.round((Number(entity.attrs.brightness) / 255) * 100)}%</span>
                          </div>
                        ) : null}
                      </div>
                    </div>

                    {/* Action buttons */}
                    {isControllable ? (
                      <div className="mt-3 flex items-center gap-2 border-t border-slate-200/80 pt-2.5">
                        {entity.domain === 'light' || entity.domain === 'switch' ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              handleControl(entity.entity_id, isOn ? 'turn_off' : 'turn_on')
                            }
                            className={`flex flex-1 items-center justify-center gap-1.5 rounded-xl border py-1.5 text-xs font-semibold transition ${
                              isOn
                                ? 'border-emerald-500/50 bg-emerald-500/20 text-emerald-800 hover:brightness-125'
                                : 'border-slate-300 bg-white text-slate-600 hover:border-cyan-500 hover:text-cyan-800'
                            }`}
                          >
                            <Power className="h-3.5 w-3.5" aria-hidden="true" />
                            {isOn ? t('turn_off') : t('turn_on')}
                          </button>
                        ) : null}

                        {entity.domain === 'cover' ? (
                          <>
                            <Btn
                              tone="slate"
                              busy={busy}
                              onClick={() => handleControl(entity.entity_id, 'open_cover')}
                            >
                              {t('open')}
                            </Btn>
                            <Btn
                              tone="slate"
                              busy={busy}
                              onClick={() => handleControl(entity.entity_id, 'close_cover')}
                            >
                              {t('close')}
                            </Btn>
                          </>
                        ) : null}

                        {entity.domain === 'climate' ? (
                          <div className="flex flex-1 items-center gap-1">
                            <Btn
                              tone="cyan"
                              busy={busy}
                              onClick={() =>
                                handleControl(entity.entity_id, 'set_temperature', {
                                  temperature: ((entity.attrs.temperature as number) || 20) + 0.5,
                                })
                              }
                            >
                              +0.5°
                            </Btn>
                            <Btn
                              tone="slate"
                              busy={busy}
                              onClick={() =>
                                handleControl(entity.entity_id, 'set_temperature', {
                                  temperature: ((entity.attrs.temperature as number) || 20) - 0.5,
                                })
                              }
                            >
                              -0.5°
                            </Btn>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}

      {/* TAB 2: ROOMS & FLOORS */}
      {tab === 'rooms' ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-3">
            <div>
              <h3 className="text-sm font-bold text-slate-800">{t('tab_rooms')}</h3>
              <p className="text-xs text-slate-500">
                Integrazione bidirezionale con l'applicazione Gestione Piani e Stanze (Places)
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Btn tone="cyan" busy={busy} onClick={handleSyncPlaces} title={t('sync_places')}>
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                {t('sync_places')}
              </Btn>
              <Btn tone="slate" onClick={() => openApp?.({ appId: 'places' })} title={t('open_places_app')}>
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                {t('open_places_app')}
              </Btn>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {rooms.map((room) => (
              <Panel
                key={room.area_id}
                title={room.name}
                icon={<Home className="h-4 w-4 text-cyan-600" aria-hidden="true" />}
                actions={
                  <Pill tone={room.occupied ? 'emerald' : 'slate'}>
                    {room.occupied ? t('occupied') : t('free')}
                  </Pill>
                }
              >
                <div className="space-y-3">
                  {room.floor_name ? (
                    <div className="text-xs font-semibold text-slate-500">
                      Piano: <span className="text-slate-800">{room.floor_name}</span>
                    </div>
                  ) : null}

                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2 text-center">
                      <div className="text-[10px] font-semibold text-slate-500 uppercase">{t('temperature')}</div>
                      <div className="font-mono text-sm font-bold text-amber-700">
                        {room.temperature !== undefined ? `${room.temperature} °C` : '—'}
                      </div>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-2 text-center">
                      <div className="text-[10px] font-semibold text-slate-500 uppercase">{t('humidity')}</div>
                      <div className="font-mono text-sm font-bold text-cyan-700">
                        {room.humidity !== undefined ? `${room.humidity} %` : '—'}
                      </div>
                    </div>
                  </div>

                  {/* Devices in room */}
                  <div className="rounded-xl border border-slate-200/80 bg-slate-50/40 p-2.5">
                    <div className="mb-1.5 flex items-center justify-between text-xs font-semibold text-slate-500">
                      <span>Dispositivi ({room.entities_count})</span>
                    </div>
                    <div className="max-h-36 overflow-y-auto space-y-1">
                      {room.entities.map((e) => (
                        <div
                          key={e.entity_id}
                          className="flex items-center justify-between text-[11px] text-slate-600"
                        >
                          <span className="truncate">{e.name}</span>
                          <span
                            className={`font-mono text-[10px] ${
                              e.state === 'on' ? 'text-emerald-600' : 'text-slate-500'
                            }`}
                          >
                            {e.state}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </Panel>
            ))}
          </div>
        </div>
      ) : null}

      {/* TAB 3: AUTOMATIONS */}
      {tab === 'automations' ? (
        <Panel
          title={t('tab_automations')}
          icon={<Play className="h-4 w-4 text-cyan-600" aria-hidden="true" />}
        >
          {automations.length === 0 ? (
            <Empty>Nessuna automazione trovata in Home Assistant</Empty>
          ) : (
            <List>
              {automations.map((auto) => {
                const isOn = auto.state === 'on';
                return (
                  <Row
                    key={auto.entity_id}
                    actions={
                      <div className="flex items-center gap-2">
                        <Btn
                          tone={isOn ? 'emerald' : 'slate'}
                          busy={busy}
                          onClick={() => handleToggleAuto(auto)}
                          title="Attiva / Disattiva"
                        >
                          <Power className="h-3.5 w-3.5" aria-hidden="true" />
                          {isOn ? 'Attiva' : 'Spenta'}
                        </Btn>
                        <Btn
                          tone="cyan"
                          busy={busy}
                          onClick={() => handleRunAuto(auto)}
                          title={t('run_now')}
                        >
                          <Play className="h-3.5 w-3.5" aria-hidden="true" />
                          {t('run_now')}
                        </Btn>
                      </div>
                    }
                  >
                    <div>
                      <div className="font-bold text-slate-900">{auto.alias}</div>
                      {auto.description ? (
                        <div className="text-xs text-slate-500">{auto.description}</div>
                      ) : null}
                      <div className="font-mono text-[10px] text-slate-500">
                        {auto.entity_id} {auto.last_triggered ? `· Ultima: ${auto.last_triggered}` : ''}
                      </div>
                    </div>
                  </Row>
                );
              })}
            </List>
          )}
        </Panel>
      ) : null}

      {/* TAB 4: SCENES */}
      {tab === 'scenes' ? (
        <Panel
          title={t('tab_scenes')}
          icon={<Layers className="h-4 w-4 text-cyan-600" aria-hidden="true" />}
        >
          {sceneEntities.length === 0 ? (
            <Empty>Nessuna scena configurata in Home Assistant</Empty>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
              {sceneEntities.map((scene) => (
                <div
                  key={scene.entity_id}
                  className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/80 p-3.5"
                >
                  <div className="min-w-0 flex-1">
                    <h4 className="truncate text-sm font-bold text-slate-800">{scene.name}</h4>
                    <p className="font-mono text-[10px] text-slate-500">{scene.entity_id}</p>
                  </div>
                  <Btn
                    tone="cyan"
                    busy={busy}
                    onClick={() => handleControl(scene.entity_id, 'turn_on')}
                  >
                    {t('activate')}
                  </Btn>
                </div>
              ))}
            </div>
          )}
        </Panel>
      ) : null}

      {/* TAB 5: ENERGY & POWER */}
      {tab === 'energy' ? (
        <div className="space-y-4">
          <Panel
            title={t('energy_overview')}
            icon={<Zap className="h-4 w-4 text-amber-600" aria-hidden="true" />}
            actions={
              <Btn
                tone="cyan"
                onClick={() => handleAskAssist('quanto sta assorbendo tutta la casa?')}
                busy={assistBusy}
              >
                <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
                {t('quick_test_energy')}
              </Btn>
            }
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-amber-500/40 bg-gradient-to-br from-amber-950/40 to-slate-50 p-4 text-center">
                <div className="text-xs font-semibold uppercase tracking-wider text-amber-700">
                  {t('instant_power')}
                </div>
                <div className="mt-2 font-mono text-3xl font-black text-amber-600">
                  {energy?.summary.total_power_w ?? '—'} <span className="text-lg">W</span>
                </div>
                <div className="mt-1 text-[11px] text-slate-500">Potenza istantanea assorbita</div>
              </div>

              <div className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-950/40 to-slate-50 p-4 text-center">
                <div className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
                  {t('solar_power')}
                </div>
                <div className="mt-2 font-mono text-3xl font-black text-emerald-600">
                  {energy?.summary.total_solar_w ?? '—'} <span className="text-lg">W</span>
                </div>
                <div className="mt-1 text-[11px] text-slate-500">Impianto fotovoltaico / solare</div>
              </div>

              <div className="rounded-2xl border border-cyan-500/40 bg-gradient-to-br from-cyan-950/40 to-slate-50 p-4 text-center">
                <div className="text-xs font-semibold uppercase tracking-wider text-cyan-700">
                  {t('net_power')}
                </div>
                <div className="mt-2 font-mono text-3xl font-black text-cyan-600">
                  {energy?.summary.net_power_w ?? '—'} <span className="text-lg">W</span>
                </div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {energy?.summary.net_power_w == null ? t('data_unavailable') : energy.summary.net_power_w >= 0 ? 'Prelievo da rete' : 'Immissione in rete'}
                </div>
              </div>
            </div>

            {/* Live speech feedback if tested */}
            {assistResult ? (
              <div className="mt-4 rounded-xl border border-amber-500/50 bg-amber-950/40 p-3.5">
                <div className="text-xs font-bold text-amber-700">Risposta Assist / Sensore Reale:</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">{assistResult.speech}</div>
                {assistResult.source ? (
                  <div className="mt-1 font-mono text-[10px] text-slate-500">
                    Sorgente: {assistResult.source}
                  </div>
                ) : null}
              </div>
            ) : null}
          </Panel>

          {/* Breakdown per sensor */}
          <Panel
            title={t('consumption_breakdown')}
            icon={<Sliders className="h-4 w-4 text-slate-500" aria-hidden="true" />}
          >
            {(!energy || energy.power_sensors.length === 0) ? (
              <Empty>Nessun sensore di potenza rilevato</Empty>
            ) : (
              <List>
                {energy.power_sensors.map((s) => (
                  <Row
                    key={s.entity_id}
                    actions={
                      <div className="font-mono text-sm font-bold text-amber-600">
                        {s.power_w != null ? `${s.power_w} W` : s.state == null ? t('data_unavailable') : `${s.raw_state || ''} ${s.unit}`}
                      </div>
                    }
                  >
                    <div>
                      <div className="font-semibold text-slate-800">{s.name}</div>
                      <div className="font-mono text-[10px] text-slate-500">{s.entity_id}</div>
                    </div>
                  </Row>
                ))}
              </List>
            )}
          </Panel>
        </div>
      ) : null}

      {/* TAB 6: ASSIST & PHRASES */}
      {tab === 'assist' ? (
        <div className="space-y-4">
          <Panel
            title={t('assist_title')}
            icon={<MessageSquare className="h-4 w-4 text-cyan-600" aria-hidden="true" />}
          >
            <p className="mb-3 text-xs text-slate-500">{t('assist_subtitle')}</p>

            {/* Quick chips */}
            <div className="mb-3 flex flex-wrap gap-2">
              {[
                'quanto sta assorbendo tutta la casa?',
                'quanta potenza sta consumando la casa?',
                'quanti gradi ci sono in casa?',
                'spegni tutte le luci',
                'com’è la situazione a casa?',
              ].map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => {
                    setAssistQuery(chip);
                    void handleAskAssist(chip);
                  }}
                  className="rounded-lg border border-slate-300 bg-white/80 px-2.5 py-1 text-xs text-slate-600 hover:border-cyan-500 hover:text-cyan-800"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Prompt input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={assistQuery}
                onChange={(e) => setAssistQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void handleAskAssist()}
                placeholder={t('assist_prompt_placeholder')}
                className={`${inputClass} flex-1`}
              />
              <Btn tone="cyan" busy={assistBusy} onClick={() => void handleAskAssist()}>
                {t('assist_send')}
              </Btn>
            </div>

            {/* Assist Output */}
            {assistResult ? (
              <div
                className={`mt-4 rounded-2xl border p-4 ${
                  assistResult.ok
                    ? 'border-emerald-500/40 bg-emerald-950/30'
                    : 'border-rose-500/40 bg-rose-950/30'
                }`}
              >
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600">
                  {assistResult.ok ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-rose-600" aria-hidden="true" />
                  )}
                  {t('assist_response')}
                </div>
                <div className="mt-2 text-base font-medium text-slate-900">{assistResult.speech}</div>
                {assistResult.source ? (
                  <div className="mt-2 font-mono text-[11px] text-slate-500">
                    {t('assist_source')} <span className="text-cyan-700">{assistResult.source}</span>
                  </div>
                ) : null}
              </div>
            ) : null}
          </Panel>
        </div>
      ) : null}

      {/* TAB 7: SETTINGS & DETAILS */}
      {tab === 'settings' ? (
        <Panel
          title={t('connection_info')}
          icon={<Settings className="h-4 w-4 text-slate-500" aria-hidden="true" />}
          actions={
            <Btn
              tone="cyan"
              onClick={() => openApp?.({ appId: 'features_hub', initialPayload: { featureId: 'home_assistant' } })}
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              {t('open_control_panel')}
            </Btn>
          }
        >
          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                <div className="text-[10px] font-semibold uppercase text-slate-500">{t('ha_url')}</div>
                <div className="mt-1 font-mono text-xs font-bold text-slate-800">
                  {overview?.url || '—'}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                <div className="text-[10px] font-semibold uppercase text-slate-500">{t('ha_version')}</div>
                <div className="mt-1 font-mono text-xs font-bold text-slate-800">
                  {overview?.ha_version || '—'}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                <div className="text-[10px] font-semibold uppercase text-slate-500">{t('total_entities')}</div>
                <div className="mt-1 font-mono text-xs font-bold text-slate-800">
                  {overview?.entities_count ?? entities.length}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                <div className="text-[10px] font-semibold uppercase text-slate-500">{t('total_devices')}</div>
                <div className="mt-1 font-mono text-xs font-bold text-slate-800">
                  {overview?.devices_count ?? 0}
                </div>
              </div>
            </div>


          </div>
        </Panel>
      ) : null}
      {tab === 'settings' ? <ConnectionPanel t={t} onSaved={loadData} /> : null}
      {tab !== 'settings' && (overview?.status === 'not_configured' || overview?.status === 'auth_failed') ? (
        <Panel title={t('conn_title')}>
          <p className="mb-3 text-xs text-slate-500">{t(overview.status === 'auth_failed' ? 'conn_banner_auth' : 'conn_banner_missing')}</p>
          <Btn tone="cyan" onClick={() => setTab('settings')}>
            {t('conn_open')}
          </Btn>
        </Panel>
      ) : null}
    </AppFrame>
  );
}
