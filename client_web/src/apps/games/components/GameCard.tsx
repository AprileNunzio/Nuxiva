import React from 'react';
import { GameItem } from '../types';

interface GameCardProps {
  game: GameItem;
  t: (key: string, params?: Record<string, any>) => string;
  onToggleStatus: (gameId: string, currentStatus: boolean) => void;
  onLaunch: (gameId: string) => void;
  onInspect: (game: GameItem) => void;
}

export function GameCard({ game, t, onToggleStatus, onLaunch, onInspect }: GameCardProps) {
  return (
    <div className={`game-card-item ${!game.is_active ? 'disabled' : ''}`}>
      <div>
        <div className="game-card-header">
          <div className="game-card-title-group">
            <span className="game-card-icon">{game.icon}</span>
            <div>
              <h3 className="game-card-title">
                {game.name}
                <span className="game-card-version">v{game.version}</span>
              </h3>
            </div>
          </div>
          <label className="game-toggle-switch" title={t('toggle_status')}>
            <input
              type="checkbox"
              checked={game.is_active}
              onChange={() => onToggleStatus(game.game_id, game.is_active)}
            />
            <span className="game-toggle-slider" />
          </label>
        </div>

        <p className="game-card-description">{game.description}</p>

        <div className="game-badges-row">
          <span className="game-badge">
            {t('commands_count', { count: game.commands.length })}
          </span>
          <span className="game-badge">
            {t('capabilities_count', { count: game.capabilities.length })}
          </span>
          {game.tech_stack.map((tech) => (
            <span key={tech} className="game-badge game-badge-tech">
              {tech}
            </span>
          ))}
        </div>
      </div>

      <div className="game-card-actions">
        <button
          type="button"
          className="game-action-btn game-btn-inspect"
          onClick={() => onInspect(game)}
        >
          {t('inspect_commands')}
        </button>
        <button
          type="button"
          className="game-action-btn game-btn-launch"
          disabled={!game.is_active}
          onClick={() => onLaunch(game.game_id)}
        >
          {t('launch_game')}
        </button>
      </div>
    </div>
  );
}
