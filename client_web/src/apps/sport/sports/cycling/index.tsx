import { createSportModule } from '../genericSportModule';

export const CyclingModule = createSportModule({
  sportName: 'Ciclismo su Strada',
  sportIcon: '🚴',
  defaultTvChannel: 'Eurosport 1 HD',
  competitions: [
    { code: 'giro_italia', name: 'Giro d’Italia', flag: '🇮🇹', count: 21 },
    { code: 'tour_france', name: 'Tour de France', flag: '🇫🇷', count: 21 },
    { code: 'vuelta_espana', name: 'La Vuelta España', flag: '🇪🇸', count: 21 },
    { code: 'classiche', name: 'Monumento (Milano-Sanremo, Fiandre, Roubaix, Liegi, Lombardia)', flag: '🇪🇺', count: 5 },
  ],
  events: [
    {
      id: 'cy1',
      title: 'Il Lombardia - Como > Bergamo (252 km)',
      status: 'post',
      scoreOrTime: 'Vittoria Solitaria Pogacar',
      stage: 'Classica delle Foglie Morte',
      venue: 'Lombardia, Italia',
      tvChannel: 'Rai 2 HD / Eurosport 1 HD',
      details: 'Attacco a 48 km dal traguardo sul Passo di Ganda: 4° successo consecutivo',
    },
    {
      id: 'cy2',
      title: 'Milano - Sanremo (Primavera Classic)',
      status: 'pre',
      scoreOrTime: 'Marzo 2025',
      stage: 'La Classicissima di Primavera',
      venue: 'Poggio di Sanremo',
      tvChannel: 'Rai 2 HD',
    },
  ],
  standings: [
    { rank: 1, name: 'Tadej Pogačar', teamOrCountry: 'UAE Team Emirates 🇸🇮', score: '11,655 pts' },
    { rank: 2, name: 'Remco Evenepoel', teamOrCountry: 'Soudal Quick-Step 🇧🇪', score: '6,072 pts' },
    { rank: 3, name: 'Jonas Vingegaard', teamOrCountry: 'Visma | Lease a Bike 🇩🇰', score: '5,980 pts' },
    { rank: 4, name: 'Mathieu van der Poel', teamOrCountry: 'Alpecin-Deceuninck 🇳🇱', score: '4,453 pts' },
  ],
  defaultFavorites: ['Tadej Pogačar', 'Jonas Vingegaard', 'Remco Evenepoel', 'Mathieu van der Poel'],
});
