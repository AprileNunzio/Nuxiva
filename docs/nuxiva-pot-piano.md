# Piano di potenziamento di Nuxiva

Scenario di accettazione. L'utente chiede di creare un e-commerce di informatica. Nuxiva chiarisce le decisioni che cambiano il risultato, presenta un piano con criteri verificabili, avvia il lavoro in background e mostra progressi e artefatti nella panoramica del progetto.

| Fase | Intervento | Criterio di accettazione |
| --- | --- | --- |
| 1. Affidabilità | Integrare nel daemon Rust assegnazioni con scadenza e generazione, revoca e checkpoint di revisione. | Un riavvio durante la revisione riprende dal checkpoint. Un agente revocato perde accesso agli strumenti e i suoi aggiornamenti tardivi vengono rifiutati. |
| 2. Pianificazione | Estendere il DAG esistente con decisioni, domande aperte, budget e prove di completamento. | Una richiesta ambigua produce domande mirate. I task indipendenti procedono in parallelo e ogni consegna ha verifiche riproducibili. |
| 3. Repository grandi | Evolvere agency-codeindex con aggiornamenti incrementali, limiti e misure di prestazioni. | Misurare ricerca, memoria e aggiornamenti su un corpus di un milione di file. Pubblicare configurazione e risultati riproducibili. |
| 4. Strumenti | Applicare permessi per progetto e tentativo. Generare nuovi strumenti come proposte versionate, con test isolati e approvazione prima dell'attivazione. | Uno strumento revocato o privo di permessi non può accedere a dati, rete o scritture fuori ambito. |
| 5. Panoramica | Collegare elenco e dettaglio allo stato persistente dei progetti. Usare le stesse azioni per tastiera, touch, voce e gesti. | Selezione e aggiornamenti funzionano anche con soli progetti in pausa o conclusi. Ogni azione è accessibile senza microfono o fotocamera. |
| 6. Consegna | Validare il percorso completo con il progetto e-commerce di riferimento. | Dalla richiesta si arriva ad artefatti e prove, con ripresa dopo riavvio e annullamento durante il lavoro. |

Il daemon Rust è la fonte dello stato operativo. La migrazione del bridge procede per capacità, mantenendo verificabile la compatibilità a ogni passaggio. La vista esistente di Display è la base per la panoramica, con testi localizzati e layout adattivo. La pubblicazione di ogni fase segue i relativi test di accettazione.
