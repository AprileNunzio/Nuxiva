import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Music4 } from 'lucide-react';
import { useWindowNodeContext } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { usePlayhead } from './usePlayhead';
import { useStudio } from './useStudio';
import { Arrangement } from './components/Arrangement';
import { CastPanel } from './components/Cast';
import { Chat } from './components/Chat';
import { Inspector } from './components/Inspector';
import { Lyrics } from './components/Lyrics';
import { Mixer } from './components/Mixer';
import { PianoRoll } from './components/PianoRoll';
import { Sidebar } from './components/Sidebar';
import { Transport } from './components/Transport';
import { Tabs } from './components/ui';

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/musicstudio');
  const studio = useStudio();
  const { project, catalog } = studio;
  const head = usePlayhead(studio.player, !!project);
  const [side, setSide] = useState('inspector');
  const [low, setLow] = useState('roll');
  const [loop, setLoop] = useState(false);
  const [track, setTrack] = useState('');
  const [clip, setClip] = useState('');
  const [wantsTalk, setWantsTalk] = useState(false);
  const { payload } = useWindowNodeContext();
  const handled = useRef('');

  useEffect(() => {
    const id = typeof payload?.project === 'string' ? payload.project : '';
    if (!id || !catalog || handled.current === id) return;
    handled.current = id;
    void (async () => {
      await studio.open(id);
      if (payload?.tab === 'chat') setSide('chat');
      if (payload?.play === true) await studio.player.current?.play();
      if (payload?.talk === true) setWantsTalk(true);
    })();
  }, [payload, catalog, studio]);

  useEffect(() => {
    if (wantsTalk && project && !studio.busy) {
      setWantsTalk(false);
      void studio.talk(t('chat_talk_start'));
    }
  }, [wantsTalk, project, studio, t]);

  useEffect(() => {
    if (!project) return;
    if (!project.tracks.some((tr) => tr.id === track)) {
      const first = project.tracks[0];
      setTrack(first?.id ?? '');
      setClip(first?.clips[0]?.id ?? '');
    }
  }, [project, track]);

  useEffect(() => studio.player.current?.setLoop(loop), [loop, studio.player, project?.id]);

  const selectedTrack = useMemo(() => project?.tracks.find((tr) => tr.id === track), [project, track]);
  const selectedClip = useMemo(() => selectedTrack?.clips.find((c) => c.id === clip), [selectedTrack, clip]);

  const sideTabs = [
    { id: 'inspector', label: t('tab_inspector') },
    { id: 'chat', label: t('tab_chat') },
    { id: 'lyrics', label: t('tab_lyrics') },
    { id: 'cast', label: t('tab_cast') },
  ];

  return (
    <div className="flex h-full min-h-0 w-full flex-col bg-white text-slate-800">
      {studio.error && (
        <div role="alert" className="flex items-center justify-between bg-rose-50 px-4 py-1.5 text-xs text-rose-700">
          <span>{t(`error_${studio.error}`)}</span>
          <button type="button" onClick={() => studio.setError('')} className="underline">
            {t('dismiss')}
          </button>
        </div>
      )}
      {project?.job.state === 'error' && (
        <div role="alert" className="bg-amber-50 px-4 py-1.5 text-xs text-amber-800">{t(`error_${project.job.error || 'failed'}`)}</div>
      )}
      <div className="flex min-h-0 flex-1">
        <Sidebar studio={studio} t={t} />
        {project && catalog ? (
          <>
            <main className="flex min-w-0 flex-1 flex-col">
              <Transport studio={studio} project={project} head={head} loop={loop} t={t} onLoop={() => setLoop((v) => !v)} onCast={() => setSide('cast')} />
              <Arrangement
                project={project}
                catalog={catalog}
                head={head}
                selected={track}
                clip={clip}
                onSelect={(tr, c) => {
                  setTrack(tr);
                  setClip(c);
                }}
                onSeek={(beat) => studio.player.current?.seek(beat)}
                edit={studio.edit}
              />
              <div className="flex h-72 shrink-0 flex-col border-t border-slate-200">
                <div className="w-64 p-2">
                  <Tabs
                    items={[
                      { id: 'roll', label: t('tab_roll') },
                      { id: 'mixer', label: t('tab_mixer') },
                    ]}
                    value={low}
                    onChange={setLow}
                  />
                </div>
                {low === 'roll' ? (
                  <PianoRoll project={project} catalog={catalog} track={selectedTrack} clip={selectedClip} beat={head.beat} edit={studio.edit} player={studio.player.current} t={t} />
                ) : (
                  <Mixer project={project} head={head} selected={track} onSelect={setTrack} edit={studio.edit} t={t} />
                )}
              </div>
            </main>
            <aside className="flex w-80 shrink-0 flex-col border-l border-slate-200 bg-slate-50/50">
              <div className="p-2">
                <Tabs items={sideTabs} value={side} onChange={setSide} />
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto">
                {side === 'inspector' && <Inspector studio={studio} project={project} catalog={catalog} track={selectedTrack} edit={studio.edit} t={t} />}
                {side === 'chat' && <Chat studio={studio} t={t} />}
                {side === 'lyrics' && <Lyrics studio={studio} project={project} catalog={catalog} t={t} />}
                {side === 'cast' && <CastPanel project={project} onPublish={studio.publish} t={t} />}
              </div>
            </aside>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-gradient-to-br from-violet-50 via-white to-fuchsia-50 text-center">
            <div className="rounded-3xl bg-gradient-to-br from-violet-600 to-fuchsia-600 p-5 text-white shadow-lg">
              <Music4 size={40} />
            </div>
            <h1 className="text-xl font-semibold">{t('title')}</h1>
            <p className="max-w-md text-sm text-slate-500">{t('welcome')}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default View;
