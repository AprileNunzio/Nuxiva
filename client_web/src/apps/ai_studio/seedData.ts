import type { Message } from './types';

export function getDefaultVoiceMessages(): Message[] {
  const now = Math.floor(Date.now() / 1000);
  return [
    {
      id: 'voice_msg_1',
      thread_id: 'th_live_voice_port80',
      role: 'user',
      content: 'Ciao Nuxiva, verifica lo stato dei sensori e la lavorazione del pezzo 3D per la stampa.',
      thought: '',
      reactions: [
        { emoji: '❤️', count: 1, authors: ['nuxiva'] },
        { emoji: '👍', count: 1, authors: ['nuxiva'] },
      ],
      artifacts: [],
      attachments: [],
      memory_recalls: [{
        id: 'mem_v1',
        source: 'voice_speech',
        content: 'Voce utente acquisita in duplex sulla porta 80',
        speaker: 'Utente',
        timestamp: now - 30,
        tags: ['voce', 'sensori', '3d'],
      }],
      created_at: now - 30,
    },
    {
      id: 'voice_msg_2',
      thread_id: 'th_live_voice_port80',
      role: 'assistant',
      content: 'Sensori a regime. Ho preparato il pezzo 3D parametrico con tolleranza meccanica di 0.15mm e compensazione kerf. Puoi aprire la visualizzazione della lavorazione 3D direttamente nella finestra WebGL e votare il sondaggio requisiti qui sotto.',
      thought: 'Trascrizione risposta audio duplex con modulo parametrico collegato, widget telemetria e sondaggio requisiti.',
      thinking_duration: '6m 36s',
      reactions: [
        { emoji: '🚀', count: 2, authors: ['nuxiva', 'user'] },
        { emoji: '💡', count: 1, authors: ['nuxiva'] },
        { emoji: '🎯', count: 1, authors: ['nuxiva'] },
      ],
      widgets: [
        {
          id: 'w_sensors',
          title: 'Sensori Ambientali & Hardware',
          type: 'sensors',
          data: { temp: 21.8, humidity: 46, cpu: 14, bus: 'OPERATIVO' },
        },
        {
          id: 'w_laser',
          title: 'Taglio Laser & CNC',
          type: 'laser_cnc',
          data: { power: '50W', speed: '380 mm/s', kerf: '0.14 mm', material: 'Compensato Betulla 4mm' },
        },
        {
          id: 'w_progress',
          title: 'Avanzamento Progetto Nuxiva',
          type: 'project_progress',
          data: { progress: 92, tasksDone: 19, tasksTotal: 21, level: 'Level 0 (Zero-Token SolutionBank)' },
        },
      ],
      poll: {
        id: 'poll_requirements',
        question: 'Quale strategia di lavorazione e finitura preferisci per il pezzo?',
        isComplex: true,
        currentStepIndex: 0,
        steps: [
          {
            id: 'step_tech',
            category: 'Tecnologia di Produzione',
            title: 'Scegli il metodo di fabbricazione primario',
            options: [
              { id: 'opt_laser', text: 'Taglio Laser CO2 ad Alta Precisione', votes: 1, description: 'Bordi puliti, tolleranza 0.14mm, ideale per legno, acrilico o guarnizioni.' },
              { id: 'opt_3d_fdm', text: 'Stampa 3D FDM / Resina SLA', votes: 0, description: 'Geometrie complesse interne, supporto PLA / PETG tecnico.' },
              { id: 'opt_cnc_mill', text: 'Fresatura CNC Meccanica Sottrattiva', votes: 0, description: 'Alluminio aeronautico o ottone, massima rigidità strutturale.' },
            ],
          },
          {
            id: 'step_tolerance',
            category: 'Tolleranze Meccaniche',
            title: 'Definisci il livello di accoppiamento dimensionale',
            options: [
              { id: 'opt_tol_tight', text: 'Accoppiamento di Precisione (±0.05 mm)', votes: 0, description: 'Calibrazione kerf attiva con passata di finitura.' },
              { id: 'opt_tol_standard', text: 'Accoppiamento Standard (±0.15 mm)', votes: 1, description: 'Velocità di lavorazione con compensazione standard.' },
            ],
          },
        ],
        options: [
          { id: 'opt_1', text: 'Taglio Laser CO2 (Precisione 0.14mm)', votes: 3 },
          { id: 'opt_2', text: 'Stampa 3D FDM / Resina', votes: 1 },
        ],
      },
      actions: [
        { id: 'act_1', kind: 'wait', label: 'Wait 6 seconds finished' },
        { id: 'act_2', kind: 'command', label: 'Check gh run list', detail: 'gh run list -L 6' },
        { id: 'act_3', kind: 'command', label: 'Check run 44790863567', detail: 'Check CI run logs' },
        { id: 'act_4', kind: 'task', label: 'Checked task Check run 44790863567' },
        { id: 'act_5', kind: 'command', label: 'Check run 44790863567 finished' },
        { id: 'act_6', kind: 'analyze', ext: 'ts', target: 'types.ts', lines: '#L30-73' },
        { id: 'act_7', kind: 'edit', ext: 'ts', target: 'types.ts', added: 14, removed: 1, diff_id: 'd_types' },
        { id: 'act_8', kind: 'edit', ext: 'tsx', target: 'Workpiece3DModal.tsx', added: 312, removed: 0, diff_id: 'd_workpiece' },
        { id: 'act_9', kind: 'analyze', ext: 'tsx', target: 'ProjectSidebar.tsx', lines: '#L105-170' },
        { id: 'act_10', kind: 'analyze', ext: 'tsx', target: 'ProjectSidebar.tsx', lines: '#L1-50' },
        { id: 'act_11', kind: 'edit', ext: 'tsx', target: 'ProjectSidebar.tsx', added: 77, removed: 5, diff_id: 'd_sidebar' },
        { id: 'act_12', kind: 'edit', ext: 'tsx', target: 'ConversationView.tsx', added: 187, removed: 9, diff_id: 'd_conv' },
        { id: 'act_13', kind: 'analyze', ext: 'tsx', target: 'View.tsx', lines: '#L10-60' },
        { id: 'act_14', kind: 'think', label: 'Thinking', duration: '13s' },
      ],
      diffs: [
        {
          id: 'd_types',
          filename: 'types.ts',
          ext: 'ts',
          added: 14,
          removed: 1,
          before_content: 'export interface Message {\n  id: string;\n  content: string;\n  thought: string;\n}',
          after_content: 'export interface Message {\n  id: string;\n  content: string;\n  thought: string;\n  thinking_duration?: string;\n  actions?: AgentAction[];\n  diffs?: FileDiff[];\n  reactions?: Reaction[];\n  poll?: Poll;\n  widgets?: DomainWidget[];\n}',
        },
        {
          id: 'd_workpiece',
          filename: 'Workpiece3DModal.tsx',
          ext: 'tsx',
          added: 312,
          removed: 0,
          before_content: '// File nuovo creato',
          after_content: 'import React, { useEffect, useRef, useState } from "react";\nimport * as THREE from "three";\nexport const Workpiece3DModal = () => { /* WebGL 3D CAD viewer */ };',
        },
        {
          id: 'd_sidebar',
          filename: 'ProjectSidebar.tsx',
          ext: 'tsx',
          added: 77,
          removed: 5,
          before_content: '// Project sidebar senza pin duplex',
          after_content: '// Project sidebar con pinned live voice duplex card (Pagina 80 Live)',
        },
      ],
      artifacts: [{
        id: 'art_voice_3d',
        identifier: 'cad_workpiece_preview',
        title: 'Pezzo Meccanico 3D (CAD Parametrico)',
        kind: '3d',
        language: 'openscad',
        content: '$fn=40;\ndifference() {\n  cube([60,90,30], center=true);\n  cylinder(h=35, r=12, center=true);\n}',
      }],
      attachments: [],
      memory_recalls: [],
      created_at: now - 25,
    },
  ];
}
