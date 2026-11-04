import { createSportModule } from '../genericSportModule';

export const NflModule = createSportModule({
  sportName: 'Football Americano (NFL)',
  sportIcon: '🏈',
  defaultTvChannel: 'DAZN NFL Game Pass',
  competitions: [
    { code: 'nfl_regular', name: 'NFL Regular Season', flag: '🇺🇸', count: 32 },
    { code: 'nfl_playoffs', name: 'NFL Playoffs & Super Bowl LIX', flag: '🇺🇸', count: 14 },
  ],
  events: [
    {
      id: 'nfl1',
      title: 'Kansas City Chiefs vs San Francisco 49ers',
      status: 'post',
      scoreOrTime: '28 - 18',
      stage: 'Week 7 Regular Season',
      venue: "Levi's Stadium, Santa Clara",
      tvChannel: 'DAZN NFL Game Pass',
      details: 'Patrick Mahomes guida i Chiefs alla 7ª vittoria consecutiva',
    },
    {
      id: 'nfl2',
      title: 'Detroit Lions vs Green Bay Packers',
      status: 'pre',
      scoreOrTime: 'Domenica ore 22:25',
      stage: 'NFC North Rivalry',
      venue: 'Lambeau Field, Green Bay',
      tvChannel: 'DAZN NFL Game Pass',
    },
  ],
  standings: [
    { rank: 1, name: 'Kansas City Chiefs', teamOrCountry: 'AFC West', score: '7-0' },
    { rank: 2, name: 'Detroit Lions', teamOrCountry: 'NFC North', score: '6-1' },
    { rank: 3, name: 'Buffalo Bills', teamOrCountry: 'AFC East', score: '6-2' },
    { rank: 4, name: 'Baltimore Ravens', teamOrCountry: 'AFC North', score: '5-3' },
  ],
  defaultFavorites: ['Kansas City Chiefs', 'San Francisco 49ers', 'Detroit Lions'],
});
