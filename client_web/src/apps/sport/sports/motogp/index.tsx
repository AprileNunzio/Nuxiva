import { createSportModule } from '../genericSportModule';

export const MotogpModule = createSportModule({
  sportName: 'MotoGP',
  sportIcon: '🏍️',
  defaultTvChannel: 'Sky Sport MotoGP HD',
  competitions: [
    { code: 'motogp', name: 'MotoGP World Championship', flag: '🌍', count: 22 },
    { code: 'moto2', name: 'Moto2 World Championship', flag: '🌍', count: 30 },
    { code: 'moto3', name: 'Moto3 World Championship', flag: '🌍', count: 28 },
  ],
  events: [
    {
      id: 'mgp1',
      title: 'GP Malesia - Sepang International Circuit',
      status: 'in',
      scoreOrTime: 'Gara LIVE (Giro 14/20)',
      stage: 'Corsa Principale',
      venue: 'Sepang, Malesia',
      tvChannel: 'Sky Sport MotoGP HD',
      details: 'Bagnaia in testa su Martin (+0.420s), Marquez terzo (+2.150s)',
    },
    {
      id: 'mgp2',
      title: 'GP Comunitat Valenciana - Ricardo Tormo',
      status: 'pre',
      scoreOrTime: 'Domenica 17 Nov',
      stage: 'Gran Finale Mondiale',
      venue: 'Valencia, Spagna',
      tvChannel: 'Sky Sport MotoGP HD',
    },
  ],
  standings: [
    { rank: 1, name: 'Jorge Martín', teamOrCountry: 'Prima Pramac Ducati', score: 453 },
    { rank: 2, name: 'Francesco Bagnaia', teamOrCountry: 'Ducati Lenovo Team', score: 436 },
    { rank: 3, name: 'Marc Márquez', teamOrCountry: 'Gresini Racing MotoGP', score: 356 },
    { rank: 4, name: 'Enea Bastianini', teamOrCountry: 'Ducati Lenovo Team', score: 345 },
    { rank: 5, name: 'Brad Binder', teamOrCountry: 'Red Bull KTM Factory', score: 201 },
  ],
  defaultFavorites: ['Francesco Bagnaia', 'Jorge Martín', 'Marc Márquez', 'Ducati Lenovo Team'],
});
