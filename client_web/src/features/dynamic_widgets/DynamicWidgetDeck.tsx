import React from "react";
import { useDynamicWidgets } from "./useDynamicWidgets";
import { WidgetItem } from "./types";
import { useI18n } from "../../shared/i18n/I18nContext";

export const DynamicWidgetDeck: React.FC = () => {
  const { t } = useI18n();
  const { widgets, isConnected, isLoading, refresh, executeAction } = useDynamicWidgets();

  return (
    <div className="w-full flex flex-col gap-4 p-4 bg-slate-900/60 border border-cyan-500/20 rounded-xl backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-cyan-500/20">
        <div className="flex items-center gap-3">
          <span className="text-xl">🧩</span>
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-cyan-400 uppercase">
              {t("widgets_title")}
            </h2>
            <p className="text-xs text-slate-400">{t("widgets_subtitle")}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono border ${
              isConnected
                ? "bg-emerald-950/60 border-emerald-500/50 text-emerald-400"
                : "bg-amber-950/60 border-amber-500/50 text-amber-400"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            {t("widgets_live_stream")}
          </span>
          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition-colors"
          >
            {t("widgets_refresh")}
          </button>
        </div>
      </div>

      {widgets.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-500">
          {t("widgets_empty")}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {widgets.map((widget) => (
            <WidgetCard
              key={widget.id}
              widget={widget}
              onAction={(action, payload) => executeAction(widget.id, action, payload)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface WidgetCardProps {
  widget: WidgetItem;
  onAction: (action: string, payload?: Record<string, any>) => void;
}

const WidgetCard: React.FC<WidgetCardProps> = ({ widget, onAction }) => {
  return (
    <div className="flex flex-col justify-between p-4 bg-slate-950/70 border border-slate-800 hover:border-cyan-500/40 rounded-lg transition-all shadow-lg shadow-black/40">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl p-1.5 bg-slate-900 border border-slate-800 rounded-lg">
            {widget.icon}
          </span>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">{widget.name}</h3>
            <p className="text-xs text-slate-400 line-clamp-1">{widget.description}</p>
          </div>
        </div>
        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
          {widget.render_type}
        </span>
      </div>

      <div className="my-2 py-2 border-t border-slate-900 flex-1">
        {widget.render_type === "metric" && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(widget.state).map(([k, v]) => (
              <div key={k} className="p-2 bg-slate-900/60 rounded border border-slate-800/80">
                <span className="text-slate-400 text-[10px] block uppercase font-mono">{k}</span>
                <span className="text-cyan-300 font-semibold">{String(v)}</span>
              </div>
            ))}
          </div>
        )}

        {widget.render_type === "toggle" && (
          <div className="flex items-center justify-between p-3 bg-slate-900/80 rounded-lg border border-slate-800">
            <span className="text-xs text-slate-300 font-medium">
              {widget.state.device_name || widget.name}
            </span>
            <button
              onClick={() => onAction("toggle")}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                widget.state.is_on
                  ? "bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/50"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {widget.state.is_on ? "ON" : "OFF"}
            </button>
          </div>
        )}

        {widget.render_type === "grid" && Array.isArray(widget.state.actions) && (
          <div className="grid grid-cols-2 gap-2">
            {widget.state.actions.map((act: any) => (
              <button
                key={act.id}
                onClick={() => onAction(act.id)}
                className="flex items-center gap-2 p-2 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 hover:border-cyan-500/50 rounded text-xs transition-colors"
              >
                <span>{act.icon}</span>
                <span className="truncate">{act.label}</span>
              </button>
            ))}
          </div>
        )}

        {widget.render_type === "graph" && (
          <div className="flex flex-col gap-2 p-3 bg-slate-900/80 rounded border border-slate-800 text-xs">
            <div className="flex justify-between text-slate-400 text-[11px]">
              <span>Active Engine</span>
              <span className="text-purple-400 font-mono font-semibold">{widget.state.active_engine}</span>
            </div>
            <div className="flex justify-between text-slate-400 text-[11px]">
              <span>Latency</span>
              <span className="text-cyan-400 font-mono font-semibold">{widget.state.average_latency_ms} ms</span>
            </div>
            <div className="flex justify-between text-slate-400 text-[11px]">
              <span>Spikes/s</span>
              <span className="text-emerald-400 font-mono font-semibold">{widget.state.latent_spikes_per_sec}</span>
            </div>
          </div>
        )}

        {widget.render_type === "canvas" && (
          <div className="p-3 bg-slate-900/80 rounded border border-slate-800 text-xs flex flex-col gap-2">
            <div className="flex justify-between text-slate-400 text-[11px]">
              <span>File</span>
              <span className="text-amber-300 font-mono">{widget.state.active_file}</span>
            </div>
            <div className="flex gap-2 mt-1">
              <button
                onClick={() => onAction("zoom", { zoom: 1.2 })}
                className="flex-1 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs"
              >
                + Zoom
              </button>
              <button
                onClick={() => onAction("zoom", { zoom: 0.8 })}
                className="flex-1 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs"
              >
                - Zoom
              </button>
            </div>
          </div>
        )}

        {widget.render_type === "card" && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(widget.state).map(([k, v]) => (
              <div key={k} className="p-2 bg-slate-900/60 rounded border border-slate-800/80">
                <span className="text-slate-400 text-[10px] block uppercase font-mono">{k}</span>
                <span className="text-slate-200 font-medium">{String(v)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
