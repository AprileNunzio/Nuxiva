import { useState, useEffect, useCallback } from 'react';
import { GameManifest, GameCommand, GameCapability, CommandExecutionOutcome } from './types';

export function useGamesScanner() {
  const [games, setGames] = useState<GameManifest[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameManifest | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGames = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/v2/games');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: GameManifest[] = await res.json();
      setGames(data);
      if (data.length > 0 && !selectedGame) {
        setSelectedGame(data[0]);
      }
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load games registry');
    } finally {
      setIsLoading(false);
    }
  }, [selectedGame]);

  const selectGame = useCallback((gameId: string) => {
    const found = games.find((g) => g.game_id === gameId);
    if (found) {
      setSelectedGame(found);
    }
  }, [games]);

  const executeCommand = useCallback(
    async (gameId: string, commandId: string, parameters: Record<string, any> = {}): Promise<CommandExecutionOutcome> => {
      const res = await fetch(`/api/v2/games/${encodeURIComponent(gameId)}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command_id: commandId, parameters }),
      });
      if (!res.ok) {
        throw new Error(`Command execution error: HTTP ${res.status}`);
      }
      return await res.json();
    },
    []
  );

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  return {
    games,
    selectedGame,
    isLoading,
    error,
    refresh: fetchGames,
    selectGame,
    executeCommand,
  };
}
