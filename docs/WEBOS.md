# Nuxiva by NunzioTech — WebOS

## Italiano

La console amministrativa sulla porta 8080 usa ora una shell desktop: avvio con verifica reale del servizio, accesso autenticato, desktop essenziale, menu Start per categorie, dock delle finestre, orologio e calendario. La lingua si sceglie nel login e vale per tutta la sessione.

Le finestre supportano trascinamento, ridimensionamento in otto direzioni, affiancamento, massimizzazione, minimizzazione, primo piano e istanze indipendenti. Il workspace viene salvato per account; i payload applicativi non vengono conservati nel browser. L'apertura funziona anche su una LAN HTTP, dove `crypto.randomUUID` non è disponibile.

La scoperta delle app legge i manifest sotto `src/`; viste e icone sono caricate dalla directory del modulo. Categorie e lingue sono ricavate dai manifest e dai dizionari trovati. Le nuove app dichiarano `manifest.json`, `View.tsx`, un'icona locale e i propri file `language/*.json`. La cornice genera le toolbar e pubblica gli eventi tramite `useWindowToolbar`; il contesto nodo e il payload sono disponibili tramite `useWindowNodeContext`.

- **Rete** mostra i dispositivi restituiti dalla topologia reale, con stato, telemetria disponibile, ricerca e filtri. Le misure mancanti non vengono inventate. La potenza in W è distinta dall'energia in kWh. La vista non pretende di elencare PC LAN non ancora rilevati dal backend.
- Il **pannello del dispositivo** mantiene il target del nodo e apre gli strumenti contestuali in finestre indipendenti. La verifica di autorizzazioni e supporto rimane nelle API esistenti.
- Il **pannello di controllo generale** usa il registro delle funzionalità e gli editor di configurazione esistenti per le impostazioni condivise.
- Il **terminale** invia i messaggi all'assistente reale. I comandi diagnostici leggono salute, topologia, funzionalità e bus. Non è una shell di sistema arbitraria.
- Il **Centro Notifiche** riceve errori del frontend ed eventi dal bus SSE autenticato esistente.
- Le icone Icons8 con tecnica 3D sono conservate nelle directory delle app, con provenienza nel manifest e attribuzione nell'interfaccia.

Verifica frontend: `cd client_web && npm ci && npm test && npm run build`. La pipeline esegue ora anche i test del window store e dei manifest. La dipendenza `cryptography` è dichiarata sia per il Core Docker sia per la build alternativa: senza di essa la cache semantica impediva l'avvio del Core.

Questo incremento conserva le viste operative esistenti. La conversione completa delle loro azioni interne in toolbar dichiarative, di tutti i layout legacy in container queries e degli eventuali widget esterni richiede ulteriori migrazioni e collaudi; non costituisce una certificazione completa 8K.

Prossimi moduli richiesti: registro errori persistente, gestione RBAC, store, amministrazione degli account e backup/ripristino FTP. Dovranno essere moduli autonomi e usare registri e scanner esistenti, senza quantità o cataloghi fissati nella shell.

## English

The port 8080 administration console now uses a desktop shell with a real service boot check, authenticated login, a quiet desktop, a categorized Start menu, window dock, clock and calendar. The language selected at login applies throughout the session.

Windows support dragging, eight resize directions, snapping, maximization, minimization, pinning and independent instances. Workspaces are stored per account without persisting application payloads. Window creation also works on HTTP LANs without `crypto.randomUUID`.

Applications are discovered from manifests under `src/`; views, icons and dictionaries belong to each module. Categories and available languages come from discovered metadata. Toolbar actions and node context use common OS services instead of importing another application's UI.

**Network** reads actual backend topology, offers device cards and filters, and distinguishes measured power from unavailable data. It does not claim discovery of unmanaged LAN PCs. Each device opens its own control panel and contextual tools; existing APIs enforce access and supported operations. The desktop control panel manages shared features using the existing feature registry and settings editors.

The terminal communicates with the actual assistant and exposes read-only diagnostic commands. The notification center uses the existing authenticated SSE bus. Icons8 3D assets and their provenance stay in each application's directory.

Frontend validation: `cd client_web && npm ci && npm test && npm run build`. CI also checks window-store behavior and discovered manifests. `cryptography` is now included in both runtime requirements files to fix the Core startup failure.

Existing business views are preserved. Complete migration of their internal actions, legacy layouts and external widgets remains follow-up work; this increment is not a full 8K certification. Planned modules include persistent error logs, RBAC management, a store, account administration and FTP backup/restore.
