import { createSportModule } from '../genericSportModule';

export const RugbyModule = createSportModule({
  sportName: 'Rugby Union',
  sportIcon: '🏉',
  defaultTvChannel: 'Sky Sport Arena HD',
  competitions: [
    { code: 'six_nations', name: 'Guinness Sei Nazioni', flag: '🇪🇺', count: 6 },
    { code: 'autumn_nations', name: 'Autumn Nations Series', flag: '🌍', count: 12 },
    { code: 'urc', name: 'United Rugby Championship (URC)', flag: '🌍', count: 16 },
  ],
  events: [
    {
      id: 'rg1',
      title: 'Italia vs Argentina',
      status: 'pre',
      scoreOrTime: 'Sabato 9 Novembre 18:40',
      stage: 'Autumn Nations Series Match 1',
      venue: 'Stadio Friuli, Udine',
      tvChannel: 'Sky Sport Arena HD / TV8',
      details: 'Gli azzurri di Gonzalo Quesada affrontano i Pumas a Udine',
    },
    {
      id: 'rg2',
      title: 'Francia vs Nuova Zelanda (All Blacks)',
      status: 'pre',
      scoreOrTime: 'Sabato 16 Novembre 21:10',
      stage: 'Autumn Nations Series',
      venue: 'Stade de France, Saint-Denis',
      tvChannel: 'Sky Sport Arena HD',
    },
  ],
  standings: [
    { rank: 1, name: 'Irlanda', teamOrCountry: 'World Rugby Ranking', score: '92.12 pts' },
    { rank: 2, name: 'Sudafrica (Springboks)', teamOrCountry: 'World Rugby Ranking', score: '91.77 pts' },
    { rank: 3, name: 'Nuova Zelanda (All Blacks)', teamOrCountry: 'World Rugby Ranking', score: '88.70 pts' },
    { rank: 4, name: 'Francia', teamOrCountry: 'World Rugby Ranking', score: '86.96 pts' },
    { rank: 8, name: 'Italia', teamOrCountry: 'World Rugby Ranking', score: '79.98 pts' },
  ],
  defaultFavorites: ['Italia', 'Benetton Rugby Treviso', 'Zebre Parma', 'All Blacks'],
});
