import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { GameItem, GameFilterStatus } from './types';
import { GamesToolbar } from './components/GamesToolbar';
import { GameCard } from './components/GameCard';
import { GameDetailModal } from './components/GameDetailModal';
import './styles.css';

export function View() {
  const { t } = useScopedI18n('apps/games');
  const { openApp } = useOSApp();

  const [games, setGames] = useState<GameItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<GameFilterStatus>('all');
  const [isScanning, setIsScanning] = useState(false);
  const [inspectedGame, setInspectedGame] = useState<GameItem | null>(null);

  const fetchGames = useCallback(async () => {
    try {
      setIsScanning(true);
      const res = await fetch('/api/v2/games?include_disabled=true');
      if (res.ok) {
        const data: GameItem[] = await res.json();
        setGames(data);
      }
    } finally {
      setIsScanning(false);
    }
  }, []);

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  const handleRescan = async () => {
    try {
      setIsScanning(true);
      const res = await fetch('/api/v2/games/rescan', { method: 'POST' });
      if (res.ok) {
        const data: GameItem[] = await res.json();
        setGames(data);
      }
    } finally {
      setIsScanning(false);
    }
  };

  const handleToggleStatus = async (gameId: string, currentStatus: boolean) => {
    const nextStatus = !currentStatus;
    setGames((prev) =>
      prev.map((g) => (g.game_id === gameId ? { ...g, is_active: nextStatus } : g))
    );

    try {
      const res = await fetch(`/api/v2/games/${encodeURIComponent(gameId)}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextStatus }),
      });
      if (!res.ok) {
        setGames((prev) =>
          prev.map((g) => (g.game_id === gameId ? { ...g, is_active: currentStatus } : g))
        );
      }
    } catch {
      setGames((prev) =>
        prev.map((g) => (g.game_id === gameId ? { ...g, is_active: currentStatus } : g))
      );
    }
  };

  const handleLaunchGame = (gameId: string) => {
    openApp({ appId: gameId });
  };

  const filteredGames = useMemo(() => {
    return games.filter((g) => {
      const matchesSearch =
        g.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.commands.some((c) => c.command_id.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && g.is_active) ||
        (statusFilter === 'disabled' && !g.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [games, searchQuery, statusFilter]);

  return (
    <div className="games-manager-container">
      <GamesToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onRescan={handleRescan}
        isScanning={isScanning}
        t={t}
      />

      <div className="games-grid-scroll">
        {filteredGames.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 1rem', color: '#94a3b8' }}>
            <span style={{ fontSize: '3rem', display: 'block', marginBottom: '1rem' }}>🎮</span>
            <h3 style={{ color: '#ffffff', marginBottom: '0.5rem' }}>{t('empty_title')}</h3>
            <p>{t('empty_desc')}</p>
          </div>
        ) : (
          <div className="games-cards-grid">
            {filteredGames.map((game) => (
              <GameCard
                key={game.game_id}
                game={game}
                t={t}
                onToggleStatus={handleToggleStatus}
                onLaunch={handleLaunchGame}
                onInspect={setInspectedGame}
              />
            ))}
          </div>
        )}
      </div>

      {inspectedGame && (
        <GameDetailModal
          game={inspectedGame}
          t={t}
          onClose={() => setInspectedGame(null)}
        />
      )}
    </div>
  );
}

export default View;
