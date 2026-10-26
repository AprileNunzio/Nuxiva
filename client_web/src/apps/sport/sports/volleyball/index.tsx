import { createSportModule } from '../genericSportModule';

export const VolleyballModule = createSportModule({
  sportName: 'Pallavolo',
  sportIcon: '🏐',
  defaultTvChannel: 'Rai Sport HD',
  competitions: [
    { code: 'superlega', name: 'SuperLega Credem Banca', flag: '🇮🇹', count: 12 },
    { code: 'serie_a1_femm', name: 'Serie A1 Tigotà Femminile', flag: '🇮🇹', count: 14 },
    { code: 'cev_champions', name: 'CEV Champions League Volley', flag: '🇪🇺', count: 20 },
  ],
  events: [
    {
      id: 'vb1',
      title: 'Sir Susa Vim Perugia vs Itas Trentino',
      status: 'in',
      scoreOrTime: '2 - 1 (25-22, 21-25, 25-19, 14-11)',
      stage: 'SuperLega Big Match',
      venue: 'PalaBarton, Perugia',
      tvChannel: 'Rai Sport HD',
      details: 'Giannelli orchestra l’attacco umbro, Michieletto risponde',
    },
    {
      id: 'vb2',
      title: 'Cucine Lube Civitanova vs Vero Volley Monza',
      status: 'pre',
      scoreOrTime: 'Domenica 18:00',
      stage: 'Regular Season',
      venue: 'Eurosuole Forum, Civitanova',
      tvChannel: 'VBTV Streaming',
    },
  ],
  standings: [
    { rank: 1, name: 'Sir Susa Vim Perugia', teamOrCountry: 'Italia', score: 14 },
    { rank: 2, name: 'Itas Trentino', teamOrCountry: 'Italia', score: 12 },
    { rank: 3, name: 'Gas Sales Bluenergy Piacenza', teamOrCountry: 'Italia', score: 11 },
    { rank: 4, name: 'Rana Verona', teamOrCountry: 'Italia', score: 9 },
  ],
  defaultFavorites: ['Sir Susa Vim Perugia', 'Itas Trentino', 'Prosecco Doc Imoco Conegliano'],
});
