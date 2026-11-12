import { createSportModule } from '../genericSportModule';

export const BasketballModule = createSportModule({
  sportName: 'Pallacanestro',
  sportIcon: '🏀',
  defaultTvChannel: 'Sky Sport NBA HD',
  competitions: [
    { code: 'nba', name: 'NBA Regular Season & Finals', flag: '🇺🇸', count: 30 },
    { code: 'euroleague', name: 'EuroLeague Basketball', flag: '🇪🇺', count: 18 },
    { code: 'lba', name: 'LBA Serie A UnipolSai', flag: '🇮🇹', count: 16 },
  ],
  events: [
    {
      id: 'bk1',
      title: 'Boston Celtics vs Los Angeles Lakers',
      status: 'in',
      scoreOrTime: '88 - 82 (Q3 4:21)',
      stage: 'Regular Season NBA',
      venue: 'TD Garden, Boston',
      tvChannel: 'Sky Sport NBA HD',
      details: 'Tatum 28 pts, LeBron 22 pts, Davis 14 reb',
    },
    {
      id: 'bk2',
      title: 'Olimpia Milano vs Virtus Bologna',
      status: 'pre',
      scoreOrTime: 'Domenica 18:15',
      stage: 'LBA Serie A',
      venue: 'Unipol Forum, Assago',
      tvChannel: 'DAZN 2 HD',
    },
    {
      id: 'bk3',
      title: 'Real Madrid vs Panathinaikos',
      status: 'post',
      scoreOrTime: '90 - 86',
      stage: 'EuroLeague Round 7',
      venue: 'WiZink Center, Madrid',
      tvChannel: 'Sky Sport Arena',
      details: 'Campazzo MVP con 19 punti e 8 assist',
    },
  ],
  standings: [
    { rank: 1, name: 'Boston Celtics', teamOrCountry: 'Eastern Conference', score: '7-1' },
    { rank: 2, name: 'Cleveland Cavaliers', teamOrCountry: 'Eastern Conference', score: '8-0' },
    { rank: 3, name: 'Oklahoma City Thunder', teamOrCountry: 'Western Conference', score: '7-0' },
    { rank: 4, name: 'Phoenix Suns', teamOrCountry: 'Western Conference', score: '6-1' },
    { rank: 5, name: 'Golden State Warriors', teamOrCountry: 'Western Conference', score: '6-2' },
  ],
  defaultFavorites: ['Boston Celtics', 'Golden State Warriors', 'Olimpia Milano', 'Virtus Bologna'],
});
