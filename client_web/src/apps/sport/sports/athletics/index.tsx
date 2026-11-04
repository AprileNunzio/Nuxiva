import { createSportModule } from '../genericSportModule';

export const AthleticsModule = createSportModule({
  sportName: 'Atletica & Nuoto',
  sportIcon: '🏊',
  defaultTvChannel: 'Rai Sport HD',
  competitions: [
    { code: 'diamond_league', name: 'Wanda Diamond League', flag: '🌍', count: 15 },
    { code: 'world_athletics', name: 'World Athletics Championships', flag: '🌍', count: 200 },
    { code: 'world_aquatics', name: 'World Aquatics Championships', flag: '🌍', count: 180 },
  ],
  events: [
    {
      id: 'at1',
      title: 'Golden Gala Pietro Mennea - Roma',
      status: 'post',
      scoreOrTime: 'Finale 100m Uomini',
      stage: 'Diamond League Roma',
      venue: 'Stadio Olimpico, Roma',
      tvChannel: 'Rai Sport HD',
      details: 'Tebogo vince in 9.87s, Jacobs terzo in 9.92s',
    },
    {
      id: 'at2',
      title: 'Salto in Alto - Gianmarco Tamberi',
      status: 'post',
      scoreOrTime: '2.37 m (Oro Europeo)',
      stage: 'Golden Gala Roma',
      venue: 'Stadio Olimpico, Roma',
      tvChannel: 'Rai Sport HD',
      details: 'Spettacolo di Gimbo Tamberi davanti a 40.000 spettatori',
    },
  ],
  standings: [
    { rank: 1, name: 'Armand Duplantis', teamOrCountry: 'Svezia 🇸🇪 (Asta 6.26m RM)', score: 'WR' },
    { rank: 2, name: 'Gianmarco Tamberi', teamOrCountry: 'Italia 🇮🇹 (Salto in Alto)', score: 'Gold' },
    { rank: 3, name: 'Marcell Jacobs', teamOrCountry: 'Italia 🇮🇹 (100m)', score: '9.85s' },
    { rank: 4, name: 'Thomas Ceccon', teamOrCountry: 'Italia 🇮🇹 (100m Dorso)', score: 'WR' },
  ],
  defaultFavorites: ['Gianmarco Tamberi', 'Marcell Jacobs', 'Armand Duplantis', 'Thomas Ceccon', 'Benedetta Pilato'],
});
