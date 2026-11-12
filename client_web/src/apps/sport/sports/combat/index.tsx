import { createSportModule } from '../genericSportModule';

export const CombatModule = createSportModule({
  sportName: 'Boxe & MMA',
  sportIcon: '🥊',
  defaultTvChannel: 'DAZN Fight Channel',
  competitions: [
    { code: 'ufc', name: 'UFC Ultimate Fighting Championship', flag: '🇺🇸', count: 12 },
    { code: 'wba_wbc', name: 'Campionato Mondiale Boxe Pesi Massimi', flag: '🌍', count: 4 },
    { code: 'bellator', name: 'Bellator Champions Series', flag: '🌍', count: 8 },
  ],
  events: [
    {
      id: 'cb1',
      title: 'Islam Makhachev vs Arman Tsarukyan',
      status: 'pre',
      scoreOrTime: 'Sabato Notte ore 04:00',
      stage: 'UFC Titolo Pesi Leggeri',
      venue: 'T-Mobile Arena, Las Vegas',
      tvChannel: 'DAZN Fight Channel',
      details: '5 Round per il titolo mondiale dei pesi leggeri UFC',
    },
    {
      id: 'cb2',
      title: 'Oleksandr Usyk vs Tyson Fury 2',
      status: 'pre',
      scoreOrTime: '21 Dicembre',
      stage: 'Rivincita Mondiale Pesi Massimi',
      venue: 'Kingdom Arena, Riyadh',
      tvChannel: 'DAZN PPV HD',
    },
  ],
  standings: [
    { rank: 1, name: 'Islam Makhachev', teamOrCountry: 'Pound-for-Pound #1 (MMA)', score: '26-1-0' },
    { rank: 2, name: 'Alex Pereira', teamOrCountry: 'Campione Massimi Leggeri', score: '12-2-0' },
    { rank: 3, name: 'Jon Jones', teamOrCountry: 'Campione Pesi Massimi UFC', score: '27-1-0' },
    { rank: 4, name: 'Oleksandr Usyk', teamOrCountry: 'Campione Indiscusso Boxe Massimi', score: '22-0-0' },
  ],
  defaultFavorites: ['Alex Pereira', 'Islam Makhachev', 'Oleksandr Usyk'],
});
