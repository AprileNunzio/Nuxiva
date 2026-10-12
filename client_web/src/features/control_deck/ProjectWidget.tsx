import React, { useEffect, useState } from 'react';
import { Folder, X, MessageSquare, Users, ShieldAlert, Cpu, Activity, CheckCircle2 } from 'lucide-react';
import { useI18n } from '../../shared/i18n/I18nContext';

interface WarRoomMessage {
    message_id: string;
    timestamp: number;
    sender_id: string;
    sender_name: string;
    sender_role: string;
    message_type: 'thought' | 'action' | 'critique' | 'deliverable' | 'alert' | 'user_input';
    content: string;
}

interface Milestone {
    milestone_id: string;
    title: string;
    description?: string;
    status: string;
    progress: number;
    assigned_agent_id?: string;
}

interface ProjectState {
    project_id: string;
    name: string;
    goal: string;
    status: string;
    autonomous_247?: boolean;
    completion_percentage?: number;
    assigned_agents?: string[];
    loop_warnings_count?: number;
    milestones?: Milestone[];
    war_room_feed?: WarRoomMessage[];
    chat_history?: {user?: string, agent?: string}[];
}

export const ProjectWidget: React.FC = () => {
    const { t } = useI18n();
    const [project, setProject] = useState<ProjectState | null>(null);
    const [projectsList, setProjectsList] = useState<ProjectState[] | null>(null);
    const [expanded, setExpanded] = useState(false);
    const [activeTab, setActiveTab] = useState<'warroom' | 'milestones' | 'team'>('warroom');
    const [newMessage, setNewMessage] = useState('');

    useEffect(() => {
        fetch('/api/v1/projects')
            .then(res => res.json())
            .then(data => {
                if (data.projects && data.projects.length > 0) {
                    const active = data.projects.find((p: ProjectState) => p.status === 'ACTIVE');
                    if (active) setProject(active);
                    else setProjectsList(data.projects);
                }
            })
            .catch(() => {});

        const hudInterval = setInterval(() => {
            fetch('/api/v1/presence/hud/projects')
                .then(res => res.json())
                .then(hud => {
                    if (hud.unlocked && hud.projects && hud.projects.length > 0) {
                        setExpanded(true);
                    }
                })
                .catch(() => {});
        }, 5000);

        return () => clearInterval(hudInterval);
    }, []);

    const sendWarRoomMessage = async () => {
        if (!newMessage.trim() || !project) return;
        try {
            await fetch(`/api/v1/projects/${project.project_id}/war-room/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender_id: 'user_primary',
                    sender_name: 'Nunzio (Owner)',
                    sender_role: t('proj_human_overseer'),
                    message_type: 'user_input',
                    content: newMessage,
                }),
            });
            const res = await fetch(`/api/v1/projects/${project.project_id}`);
            const data = await res.json();
            if (data.project) setProject(data.project);
            setNewMessage('');
        } catch (e) {}
    };

    if (!project && (!projectsList || projectsList.length === 0)) return null;

    const progressPct = Math.round(project?.completion_percentage || 0);

    return (
        <div className="fixed bottom-4 sm:bottom-6 8k:bottom-12 right-4 sm:right-6 8k:right-12 z-50 flex flex-col items-end">
            {expanded && project && (
                <div className="bg-slate-900/95 backdrop-blur-2xl border border-indigo-500/30 shadow-2xl shadow-black/60 rounded-2xl 8k:rounded-3xl w-[calc(100vw-2rem)] sm:w-[480px] 8k:w-[680px] mb-3 sm:mb-4 overflow-hidden animate-fade-in flex flex-col max-h-[80vh] sm:max-h-[620px] 8k:max-h-[850px]">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-indigo-950/80 via-slate-900/90 to-purple-950/80 p-3.5 sm:p-4 8k:p-6 border-b border-slate-700/50 flex justify-between items-start">
                        <div className="min-w-0 pr-3 sm:pr-4 flex-1">
                            <div className="flex items-center gap-2">
                                <Folder className="w-5 h-5 8k:w-7 8k:h-7 text-indigo-400 shrink-0" />
                                <h3 className="font-['Rajdhani'] font-bold text-slate-100 text-base sm:text-lg 8k:text-2xl truncate">
                                    {project.name}
                                </h3>
                                {project.autonomous_247 && (
                                    <span className="bg-emerald-500/20 text-emerald-300 text-[10px] 8k:text-sm font-mono px-2 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1 shrink-0">
                                        <Activity className="w-3 h-3 8k:w-4 8k:h-4 animate-pulse" /> {t('proj_active_247')}
                                    </span>
                                )}
                            </div>
                            <p className="text-xs 8k:text-base text-indigo-200/70 truncate mt-1 font-mono">{project.goal}</p>
                            
                            {/* Progress bar */}
                            <div className="mt-3">
                                <div className="flex justify-between text-[11px] 8k:text-sm font-mono text-slate-300 mb-1">
                                    <span>{t('proj_global_progress')}:</span>
                                    <span className="font-bold text-indigo-400">{progressPct}%</span>
                                </div>
                                <div className="w-full bg-slate-800 rounded-full h-2 8k:h-3.5 overflow-hidden border border-slate-700/50">
                                    <div 
                                        className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-2 8k:h-3.5 rounded-full transition-all duration-500"
                                        style={{ width: `${progressPct}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                        <button 
                            onClick={() => setExpanded(false)} 
                            className="text-slate-400 hover:text-white transition-colors p-1.5 8k:p-3 bg-black/30 rounded-lg 8k:rounded-xl shrink-0"
                            aria-label={t('close')}
                        >
                            <X className="w-4 h-4 8k:w-6 8k:h-6" />
                        </button>
                    </div>

                    {/* Navigation Tabs */}
                    <div className="flex border-b border-slate-800 bg-slate-950/50 text-xs 8k:text-base font-mono">
                        <button
                            onClick={() => setActiveTab('warroom')}
                            className={`flex-1 py-2 sm:py-2.5 8k:py-4 text-center flex items-center justify-center gap-1.5 transition-colors ${
                                activeTab === 'warroom' 
                                    ? 'text-indigo-400 border-b-2 border-indigo-500 font-bold bg-indigo-950/20' 
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            <MessageSquare className="w-3.5 h-3.5 8k:w-5 8k:h-5" /> {t('proj_tab_warroom')} ({project.war_room_feed?.length || 0})
                        </button>
                        <button
                            onClick={() => setActiveTab('milestones')}
                            className={`flex-1 py-2 sm:py-2.5 8k:py-4 text-center flex items-center justify-center gap-1.5 transition-colors ${
                                activeTab === 'milestones' 
                                    ? 'text-indigo-400 border-b-2 border-indigo-500 font-bold bg-indigo-950/20' 
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            <CheckCircle2 className="w-3.5 h-3.5 8k:w-5 8k:h-5" /> {t('proj_tab_milestones')} ({project.milestones?.length || 0})
                        </button>
                        <button
                            onClick={() => setActiveTab('team')}
                            className={`flex-1 py-2 sm:py-2.5 8k:py-4 text-center flex items-center justify-center gap-1.5 transition-colors ${
                                activeTab === 'team' 
                                    ? 'text-indigo-400 border-b-2 border-indigo-500 font-bold bg-indigo-950/20' 
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            <Users className="w-3.5 h-3.5 8k:w-5 8k:h-5" /> {t('proj_tab_team')} ({project.assigned_agents?.length || 0})
                        </button>
                    </div>

                    {/* Tab Contents */}
                    <div className="p-3 sm:p-4 8k:p-6 flex-1 h-64 sm:h-72 8k:h-96 overflow-y-auto space-y-3 8k:space-y-4 font-sans">
                        {activeTab === 'warroom' && (
                            <div className="space-y-3 8k:space-y-4">
                                {project.loop_warnings_count && project.loop_warnings_count > 0 ? (
                                    <div className="p-2.5 8k:p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center gap-2 text-xs 8k:text-base text-amber-300">
                                        <ShieldAlert className="w-4 h-4 8k:w-6 8k:h-6 text-amber-400 shrink-0" />
                                        <span>
                                            {t('proj_loop_warning_prefix')} <b>{project.loop_warnings_count}</b> {t('proj_loop_warning_suffix')}
                                        </span>
                                    </div>
                                ) : null}

                                {(project.war_room_feed || []).map((msg, i) => (
                                    <div key={i} className="text-xs 8k:text-base p-2.5 sm:p-3 8k:p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1">
                                        <div className="flex justify-between items-center text-[10px] 8k:text-sm font-mono text-slate-400">
                                            <span className="font-bold text-indigo-300">{msg.sender_name} ({msg.sender_role})</span>
                                            <span className="px-1.5 py-0.5 rounded bg-slate-800 uppercase">{msg.message_type}</span>
                                        </div>
                                        <div className="text-slate-200 leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {activeTab === 'milestones' && (
                            <div className="space-y-2 8k:space-y-3">
                                {(project.milestones || []).map((m, i) => (
                                    <div key={i} className="p-2.5 sm:p-3 8k:p-4 bg-slate-800/40 border border-slate-700/40 rounded-xl text-xs 8k:text-base space-y-2">
                                        <div className="flex justify-between items-center">
                                            <span className="font-bold text-slate-200">{m.title}</span>
                                            <span className="text-[10px] 8k:text-sm font-mono px-2 py-0.5 bg-indigo-900/40 text-indigo-300 rounded-md">
                                                {m.status} ({Math.round(m.progress * 100)}%)
                                            </span>
                                        </div>
                                        {m.description && <p className="text-[11px] 8k:text-sm text-slate-400">{m.description}</p>}
                                        <div className="w-full bg-slate-900 rounded-full h-1.5 8k:h-2.5 overflow-hidden">
                                            <div 
                                                className="bg-indigo-500 h-1.5 8k:h-2.5 rounded-full" 
                                                style={{ width: `${Math.round(m.progress * 100)}%` }} 
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {activeTab === 'team' && (
                            <div className="space-y-2 8k:space-y-3">
                                {(project.assigned_agents || []).map((ag, i) => (
                                    <div key={i} className="p-2.5 8k:p-4 bg-slate-800/40 border border-slate-700/40 rounded-xl flex items-center justify-between text-xs 8k:text-base">
                                        <div className="flex items-center gap-2.5">
                                            <Cpu className="w-4 h-4 8k:w-6 8k:h-6 text-indigo-400" />
                                            <div>
                                                <div className="font-bold text-slate-200 font-mono">{ag}</div>
                                                <div className="text-[10px] 8k:text-sm text-slate-400">{t('proj_autonomous_specialist')}</div>
                                            </div>
                                        </div>
                                        <span className="w-2 h-2 8k:w-3.5 8k:h-3.5 rounded-full bg-emerald-400 animate-pulse" />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* War room message composer */}
                    {activeTab === 'warroom' && (
                        <div className="p-2.5 sm:p-3 8k:p-5 border-t border-slate-800 bg-slate-950/80 flex gap-2">
                            <input
                                type="text"
                                value={newMessage}
                                onChange={(e) => setNewMessage(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && sendWarRoomMessage()}
                                placeholder={t('proj_placeholder')}
                                className="flex-1 bg-slate-900 border border-slate-700/70 rounded-xl 8k:rounded-2xl px-3 py-2 8k:px-5 8k:py-3.5 text-xs 8k:text-base text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                            />
                            <button
                                onClick={sendWarRoomMessage}
                                className="bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-2 8k:px-6 8k:py-3.5 rounded-xl 8k:rounded-2xl text-xs 8k:text-base font-semibold transition-colors shrink-0"
                            >
                                {t('send')}
                            </button>
                        </div>
                    )}
                </div>
            )}

            {!expanded && (
                <button 
                    onClick={() => setExpanded(true)}
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white p-3 sm:p-3.5 8k:p-6 rounded-full shadow-lg shadow-indigo-900/50 border border-indigo-400/30 transition-all flex items-center gap-2.5 sm:gap-3 8k:gap-5 animate-fade-in cursor-pointer group"
                    aria-label={t('proj_war_room_title')}
                >
                    <Folder className="w-4 h-4 sm:w-5 sm:h-5 8k:w-8 8k:h-8" />
                    <span className="font-['Rajdhani'] font-semibold pr-1.5 sm:pr-2 text-xs sm:text-sm 8k:text-2xl">
                        {t('proj_war_room_title')} ({progressPct}%)
                    </span>
                </button>
            )}
        </div>
    );
};
