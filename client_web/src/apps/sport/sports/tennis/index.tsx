import { createSportModule } from '../genericSportModule';

export const TennisModule = createSportModule({
  sportName: 'Tennis',
  sportIcon: '🎾',
  defaultTvChannel: 'Sky Sport Tennis HD',
  competitions: [
    { code: 'atp_finals', name: 'Nitto ATP Finals Torino', flag: '🇮🇹', count: 8 },
    { code: 'wimbledon', name: 'Wimbledon Championships', flag: '🇬🇧', count: 128 },
    { code: 'roland_garros', name: 'Roland Garros', flag: '🇫🇷', count: 128 },
    { code: 'us_open', name: 'US Open New York', flag: '🇺🇸', count: 128 },
    { code: 'australian_open', name: 'Australian Open Melbourne', flag: '🇦🇺', count: 128 },
  ],
  events: [
    {
      id: 'tn1',
      title: 'Jannik Sinner vs Carlos Alcaraz',
      status: 'in',
      scoreOrTime: '6-4, 4-6, 3-2 (40-30)',
      stage: 'Semifinale Nitto ATP Finals',
      venue: 'Inalpi Arena, Torino',
      tvChannel: 'Sky Sport Tennis HD',
      details: 'Terzo set tiratissimo: Sinner avanti di un break',
    },
    {
      id: 'tn2',
      title: 'Alexander Zverev vs Daniil Medvedev',
      status: 'pre',
      scoreOrTime: 'Oggi 20:30',
      stage: 'Fase a Gironi',
      venue: 'Inalpi Arena, Torino',
      tvChannel: 'Sky Sport Tennis HD',
    },
  ],
  standings: [
    { rank: 1, name: 'Jannik Sinner', teamOrCountry: 'Italia 🇮🇹', score: '11,830 pts' },
    { rank: 2, name: 'Carlos Alcaraz', teamOrCountry: 'Spagna 🇪🇸', score: '7,120 pts' },
    { rank: 3, name: 'Alexander Zverev', teamOrCountry: 'Germania 🇩🇪', score: '6,795 pts' },
    { rank: 4, name: 'Novak Djokovic', teamOrCountry: 'Serbia 🇷🇸', score: '6,210 pts' },
    { rank: 5, name: 'Daniil Medvedev', teamOrCountry: 'Atleta Neutro', score: '5,530 pts' },
  ],
  defaultFavorites: ['Jannik Sinner', 'Carlos Alcaraz', 'Novak Djokovic', 'Lorenzo Musetti'],
});
