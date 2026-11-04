import { SpatialAsset } from '../../shared/types';

export const SPATIAL_ASSET_CATEGORIES = [
  { id: 'all', label: 'Tutti gli Asset', icon: 'Grid' },
  { id: 'weather', label: 'Meteo & Clima', icon: 'CloudRain' },
  { id: 'tools', label: 'Strumenti & Attrezzi', icon: 'Wrench' },
  { id: 'furniture', label: 'Arredamento & Ufficio', icon: 'Armchair' },
  { id: 'architecture', label: 'Edifici & Stanze', icon: 'Building' },
  { id: 'devices', label: 'Hardware & IoT', icon: 'Cpu' },
  { id: 'vehicles', label: 'Veicoli & Droni', icon: 'Car' },
  { id: 'fx', label: 'Effetti Particellari', icon: 'Sparkles' }
] as const;

export const SPATIAL_ASSETS_REGISTRY: SpatialAsset[] = [
  {
    id: 'prop_umbrella',
    name: 'Ombrello Tattico Idrofobico',
    category: 'weather',
    tags: ['pioggia', 'meteo', 'acqua', 'temporale', 'riparo'],
    icon: 'Umbrella',
    description: 'Ombrello cibernetico con cupola idrofobica, si apre istantaneamente quando piove o viene richiesto il meteo.',
    scale: 1.0
  },
  {
    id: 'fx_rain_storm',
    name: 'Sistema Particellare Pioggia & Tuoni',
    category: 'weather',
    tags: ['pioggia', 'temporale', 'lampi', 'meteo'],
    icon: 'CloudLightning',
    description: 'Generatore procedurale di gocce d\'acqua ad alta velocità con illuminazione a lampi stroboscopici.',
    scale: 1.0
  },
  {
    id: 'fx_snow_fall',
    name: 'Bufera di Neve Artica',
    category: 'weather',
    tags: ['neve', 'freddo', 'inverno', 'meteo'],
    icon: 'Snowflake',
    description: 'Fiocchi di neve procedurali con moto browniano e brezza simulata.',
    scale: 1.0
  },
  {
    id: 'prop_sun_shield',
    name: 'Occhiali & Scudo Termico Solare',
    category: 'weather',
    tags: ['sole', 'caldo', 'estate', 'meteo'],
    icon: 'Sun',
    description: 'Accessorio protettivo da riverbero per giornate terse e assolate.',
    scale: 1.0
  },

  {
    id: 'tool_hologram_tablet',
    name: 'Terminale Olografico HUD',
    category: 'tools',
    tags: ['terminale', 'codice', 'log', 'schermo', 'hacker'],
    icon: 'Tablet',
    description: 'Display olografico fluttuante con visualizzazione telemetrica e output di codice in tempo reale.',
    scale: 1.2
  },
  {
    id: 'tool_cad_workbench',
    name: 'Banco da Lavoro CAD 3D',
    category: 'tools',
    tags: ['cad', 'meccanica', 'flangia', 'progettazione', 'ingegneria'],
    icon: 'DraftingCompass',
    description: 'Superficie da disegno tecnico con supporto di proiezione wireframe e manipolazione di mesh meccaniche.',
    scale: 1.5
  },
  {
    id: 'tool_torque_wrench',
    name: 'Chiave Dinamometrica & Calibro',
    category: 'tools',
    tags: ['attrezzi', 'officina', 'manutenzione', 'riparazione'],
    icon: 'Wrench',
    description: 'Set di utensili digitali di precisione per task di auto-riparazione kernel e ingegneria fisica.',
    scale: 0.8
  },

  {
    id: 'device_server_rack',
    name: 'Server Rack Enterprise Datacenter',
    category: 'devices',
    tags: ['server', 'cluster', 'datacenter', 'proxmox', 'rete'],
    icon: 'Server',
    description: 'Armadio rack 42U con indicatori LED di attività, storage array e ventole attive.',
    scale: 1.6
  },
  {
    id: 'device_smart_light',
    name: 'Punto Luce Domotico RGBW',
    category: 'devices',
    tags: ['luce', 'domotica', 'home assistant', 'illuminazione'],
    icon: 'Lightbulb',
    description: 'Lampada connessa al bus domotico in grado di emettere vera illuminazione dinamica 3D nella scena.',
    scale: 1.0
  },
  {
    id: 'device_surveillance_cam',
    name: 'Torretta Visione IA 360°',
    category: 'devices',
    tags: ['telecamera', 'sorveglianza', 'visione', 'yolo', 'sicurezza'],
    icon: 'Camera',
    description: 'Modulo telecamera motorizzata con cono di proiezione volumetrico per il tracking visivo.',
    scale: 0.9
  },

  {
    id: 'furn_executive_desk',
    name: 'Scrivania Direzionale Cyber',
    category: 'furniture',
    tags: ['scrivania', 'ufficio', 'lavoro', 'computer'],
    icon: 'Laptop',
    description: 'Postazione di comando minimale in alluminio spazzolato e vetro oscurato antiriflesso.',
    scale: 1.8
  },
  {
    id: 'furn_ergonomic_chair',
    name: 'Sedia Ergonomica Aerodinamica',
    category: 'furniture',
    tags: ['sedia', 'ufficio', 'arredo'],
    icon: 'Armchair',
    description: 'Poltrona da supervisore con telaio in lega composita.',
    scale: 1.2
  },

  {
    id: 'arch_cyber_lab',
    name: 'Laboratorio IA Sotterraneo',
    category: 'architecture',
    tags: ['laboratorio', 'cyberpunk', 'neon', 'stanza'],
    icon: 'Shield',
    description: 'Stanza blindata con pareti in grafene, illuminazione al neon e cablaggi in fibra ottica a vista.',
    scale: 2.0
  },
  {
    id: 'arch_modern_living',
    name: 'Open-Space Living Panoramico',
    category: 'architecture',
    tags: ['casa', 'salotto', 'living', 'architettura'],
    icon: 'Home',
    description: 'Ambiente residenziale moderno con vetrate a tutta altezza e pavimento in resina lucida.',
    scale: 2.5
  },

  {
    id: 'veh_surveillance_drone',
    name: 'Drone da Perlustrazione Quaternario',
    category: 'vehicles',
    tags: ['drone', 'volo', 'ricognizione', 'robotica'],
    icon: 'Plane',
    description: 'Micro-drone autonomo con eliche a rotazione contrapposta per perlustrazione domestica o aziendale.',
    scale: 0.7
  },
  {
    id: 'veh_autonomous_rover',
    name: 'Rover Esploratore AGV',
    category: 'vehicles',
    tags: ['veicolo', 'robot', 'rover', 'ruote'],
    icon: 'Car',
    description: 'Piattaforma mobile con sensori LiDAR per mappatura SLAM e trasporto campioni.',
    scale: 1.2
  }
];
