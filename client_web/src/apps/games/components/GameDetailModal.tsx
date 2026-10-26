import React, { useState } from 'react';
import { GameItem } from '../types';

interface GameDetailModalProps {
  game: GameItem;
  t: (key: string, params?: Record<string, any>) => string;
  onClose: () => void;
}

export function GameDetailModal({ game, t, onClose }: GameDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'commands' | 'capabilities'>('commands');

  return (
    <div className="game-modal-backdrop" onClick={onClose}>
      <div className="game-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="game-modal-header">
          <div className="game-card-title-group">
            <span className="game-card-icon">{game.icon}</span>
            <div>
              <h3 className="game-card-title">{game.name}</h3>
              <span className="game-card-version">{game.directory_path}</span>
            </div>
          </div>
          <button type="button" className="games-filter-btn" onClick={onClose}>
            {t('modal_close')}
          </button>
        </div>

        <div className="games-header-bar" style={{ padding: '0.5rem 1.5rem' }}>
          <div className="games-filter-tabs">
            <button
              type="button"
              className={`games-filter-btn ${activeTab === 'commands' ? 'active' : ''}`}
              onClick={() => setActiveTab('commands')}
            >
              {t('tab_commands')} ({game.commands.length})
            </button>
            <button
              type="button"
              className={`games-filter-btn ${activeTab === 'capabilities' ? 'active' : ''}`}
              onClick={() => setActiveTab('capabilities')}
            >
              {t('tab_capabilities')} ({game.capabilities.length})
            </button>
          </div>
        </div>

        <div className="game-modal-body">
          {activeTab === 'commands' ? (
            <div>
              {game.commands.map((cmd) => (
                <div key={cmd.command_id} className="game-command-item">
                  <div className="game-command-name">
                    /{cmd.command_id}
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginLeft: '0.5rem' }}>
                      [{cmd.input_types.join(', ')}]
                    </span>
                  </div>

                  {cmd.voice_triggers.length > 0 && (
                    <div style={{ marginTop: '0.375rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginRight: '0.25rem' }}>
                        {t('cmd_triggers')}
                      </span>
                      {cmd.voice_triggers.map((trigger) => (
                        <span key={trigger} className="game-trigger-tag">
                          "{trigger}"
                        </span>
                      ))}
                    </div>
                  )}

                  <div style={{ marginTop: '0.375rem', fontSize: '0.75rem', color: '#cbd5e1' }}>
                    <span style={{ color: '#94a3b8' }}>{t('cmd_params')} </span>
                    {Object.keys(cmd.parameters).length > 0
                      ? JSON.stringify(cmd.parameters)
                      : t('cmd_no_params')}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div>
              {game.capabilities.map((cap) => (
                <div key={cap.capability_id} className="game-command-item">
                  <div className="game-command-name">
                    {cap.capability_id}
                    <span style={{ fontSize: '0.75rem', color: '#10b981', marginLeft: '0.5rem' }}>
                      [{cap.category}]
                    </span>
                  </div>
                  {cap.metadata && Object.keys(cap.metadata).length > 0 && (
                    <pre style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                      {JSON.stringify(cap.metadata, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
