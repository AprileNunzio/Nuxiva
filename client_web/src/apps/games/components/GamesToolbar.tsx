import React from 'react';
import { GameFilterStatus } from '../types';

interface GamesToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: GameFilterStatus;
  onStatusFilterChange: (status: GameFilterStatus) => void;
  onRescan: () => void;
  isScanning: boolean;
  t: (key: string, params?: Record<string, any>) => string;
}

export function GamesToolbar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onRescan,
  isScanning,
  t,
}: GamesToolbarProps) {
  return (
    <div className="games-header-bar">
      <div className="games-search-box">
        <input
          type="text"
          className="games-search-input"
          placeholder={t('search_placeholder')}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      <div className="games-filter-tabs">
        <button
          type="button"
          className={`games-filter-btn ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => onStatusFilterChange('all')}
        >
          {t('filter_all')}
        </button>
        <button
          type="button"
          className={`games-filter-btn ${statusFilter === 'active' ? 'active' : ''}`}
          onClick={() => onStatusFilterChange('active')}
        >
          {t('filter_active')}
        </button>
        <button
          type="button"
          className={`games-filter-btn ${statusFilter === 'disabled' ? 'active' : ''}`}
          onClick={() => onStatusFilterChange('disabled')}
        >
          {t('filter_disabled')}
        </button>
      </div>

      <button
        type="button"
        className="games-rescan-btn"
        disabled={isScanning}
        onClick={onRescan}
      >
        <span>🔄</span>
        <span>{t('rescan_games')}</span>
      </button>
    </div>
  );
}
