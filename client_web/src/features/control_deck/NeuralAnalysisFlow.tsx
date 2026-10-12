import React, { useEffect, useState } from 'react';
import { Brain, Activity, ArrowRight, Code } from 'lucide-react';
import { useI18n } from '../../shared/i18n/I18nContext';

export interface TelemetryEvent {
    id: string;
    sub_type: 'swarm_handoff' | 'agent_thought' | 'tool_execution' | 'critique_feedback';
    agent_id: string;
    timestamp: number;
    payload: Record<string, any>;
}

export const NeuralAnalysisFlow: React.FC = () => {
    const { t } = useI18n();
    const [events, setEvents] = useState<TelemetryEvent[]>([]);

    useEffect(() => {
        const ws = new WebSocket('wss://localhost:8443/bus-core');
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'telemetry') {
                    setEvents(prev => [{ ...data, id: crypto.randomUUID() }, ...prev].slice(0, 100));
                }
            } catch (e) {}
        };
        return () => ws.close();
    }, []);

    const renderIcon = (type: string) => {
        switch (type) {
            case 'swarm_handoff': return <ArrowRight className="w-4 h-4 8k:w-7 8k:h-7 text-purple-400" />;
            case 'agent_thought': return <Brain className="w-4 h-4 8k:w-7 8k:h-7 text-cyan-400" />;
            case 'tool_execution': return <Code className="w-4 h-4 8k:w-7 8k:h-7 text-amber-400" />;
            default: return <Activity className="w-4 h-4 8k:w-7 8k:h-7 text-slate-400" />;
        }
    };

    return (
        <div className="w-full bg-slate-900/60 border border-slate-800 rounded-2xl 8k:rounded-3xl p-4 sm:p-5 8k:p-8 backdrop-blur-md flex flex-col h-80 sm:h-96 8k:h-[500px]">
            <h2 className="font-['Rajdhani'] text-base sm:text-lg 8k:text-2xl font-semibold text-slate-100 mb-3 sm:mb-4 8k:mb-6 flex items-center gap-2 8k:gap-4">
                <Activity className="w-5 h-5 8k:w-8 8k:h-8 text-indigo-400" />
                {t('flow_title')}
            </h2>
            <div className="flex-1 overflow-y-auto space-y-2.5 sm:space-y-3 8k:space-y-5 pr-2 custom-scrollbar">
                {events.map((ev) => (
                    <div key={ev.id} className="bg-black/40 border border-slate-800/80 p-2.5 sm:p-3 8k:p-5 rounded-xl 8k:rounded-2xl flex gap-3 8k:gap-5 animate-fade-in">
                        <div className="mt-1 p-1.5 8k:p-2.5 rounded-lg 8k:rounded-xl bg-slate-800/50 border border-slate-700/50 h-fit shrink-0">
                            {renderIcon(ev.sub_type)}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-start mb-1">
                                <span className="text-xs 8k:text-base font-mono font-bold text-slate-300 uppercase tracking-wider">{ev.agent_id}</span>
                                <span className="text-[10px] 8k:text-sm font-mono text-slate-500">{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                            </div>
                            {ev.sub_type === 'agent_thought' && (
                                <p className="text-xs 8k:text-base text-cyan-300/90 font-mono leading-relaxed border-l-2 border-cyan-500/30 pl-2">
                                    {ev.payload.thought}
                                </p>
                            )}
                            {ev.sub_type === 'swarm_handoff' && (
                                <p className="text-xs 8k:text-base text-purple-300/90 flex items-center gap-2">
                                    {t('flow_handoff_to')} <span className="font-bold">{ev.payload.to}</span>: {ev.payload.reason}
                                </p>
                            )}
                            {ev.sub_type === 'tool_execution' && (
                                <div className="text-[11px] 8k:text-sm font-mono bg-slate-950 p-2 8k:p-3 rounded-lg border border-slate-800 text-amber-300/80 mt-1 truncate">
                                    [EXEC] {ev.payload.tool} - {ev.payload.status} ({ev.payload.detail})
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {events.length === 0 && (
                    <div className="h-full flex items-center justify-center text-slate-500 text-xs 8k:text-base font-mono animate-pulse">
                        {t('flow_waiting')}
                    </div>
                )}
            </div>
        </div>
    );
};
