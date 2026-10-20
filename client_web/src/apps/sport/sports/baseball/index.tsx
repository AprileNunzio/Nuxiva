import { createSportModule } from '../genericSportModule';

export const BaseballModule = createSportModule({
  sportName: 'Baseball (MLB)',
  sportIcon: '⚾',
  defaultTvChannel: 'Sky Sport Max HD',
  competitions: [
    { code: 'world_series', name: 'MLB World Series', flag: '🇺🇸', count: 2 },
    { code: 'alcs', name: 'American League Championship', flag: '🇺🇸', count: 2 },
    { code: 'nlcs', name: 'National League Championship', flag: '🇺🇸', count: 2 },
  ],
  events: [
    {
      id: 'bb1',
      title: 'Los Angeles Dodgers vs New York Yankees',
      status: 'post',
      scoreOrTime: '7 - 6 (Serie 4 - 1)',
      stage: 'World Series Gara 5',
      venue: 'Yankee Stadium, New York',
      tvChannel: 'Sky Sport Max HD',
      details: 'I Dodgers di Shohei Ohtani e Freddie Freeman vincono il titolo mondiale!',
    },
  ],
  standings: [
    { rank: 1, name: 'Los Angeles Dodgers', teamOrCountry: 'Campioni del Mondo 2024 🏆', score: '98-64' },
    { rank: 2, name: 'New York Yankees', teamOrCountry: 'Campioni American League', score: '94-68' },
    { rank: 3, name: 'Cleveland Guardians', teamOrCountry: 'American League', score: '92-69' },
    { rank: 4, name: 'New York Mets', teamOrCountry: 'National League', score: '89-73' },
  ],
  defaultFavorites: ['Los Angeles Dodgers', 'New York Yankees'],
});
