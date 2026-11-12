# Log di sistema

Applicazione autonoma di consultazione e diagnostica, scoperta tramite `feature.json` e manifest WebOS. Le lingue e l'icona del client sono nella directory `client_web/src/core_apps/system_logs/`.

## Dati e limiti

Le fonti locali vengono scoperte dal journal, dai servizi systemd, dai container Docker disponibili e dai file `.log` nella directory dei log Nuxiva. Il registro persistente Nuxiva rimane disponibile anche dopo un riavvio. Letture, intervalli e numero di eventi sono limitati; conteggi, grafico e analisi descrivono il campione selezionato.

Per un dispositivo remoto vengono mostrati soltanto eventi del server con `node_id` corrispondente. Non viene usata una ricerca del nome o dell'indirizzo nel testo per attribuire un evento. Journal, file, stato e hardware del server non vengono presentati come dati del dispositivo remoto. L'assenza del trasporto dei log remoti è esplicita nell'interfaccia e nel rapporto.

L'analisi riconosce alcuni problemi tecnici nei messaggi effettivi, senza dichiarare sano l'intero sistema quando non trova corrispondenze. La gravità indica se proviene dal journal, da un livello dichiarato o da un'inferenza testuale. Gli eventi privi di orario sono segnalati perché il filtro temporale non è affidabile per quei record.

## Sicurezza ed esportazione

Tutte le rotte richiedono autenticazione. `logs.read` e il nodo assegnato vengono verificati per la lettura; ogni formato esportato richiede anche `logs.export`. Percorsi privati del catalogo non sono esposti. I segreti riconoscibili sono oscurati prima di visualizzazione ed esportazione; il CSV protegge le celle che potrebbero essere interpretate come formule.

TXT, JSON e CSV esportano la selezione corrente. Il rapporto diagnostico JSON aggiunge versione dello schema, inventario delle fonti, limiti di raccolta e, esclusivamente per la macchina locale selezionata, una fotografia reale di sistema operativo, memoria e disco. Non si deve condividere un rapporto senza verificarne il contenuto: l'oscuramento automatico non identifica ogni possibile dato personale o segreto.

La gestione del dispositivo usa il pannello e i comandi Nuxiva esistenti, con le autorizzazioni amministrative richieste dalle relative API. La consultazione dei log non invia comandi di riavvio o di riconfigurazione.

## Interfaccia

Il manifest dichiara ricerca, navigazione, azioni di esportazione, capacità e barra di stato. `View.tsx` compone il kit condiviso; `api.ts` definisce gli endpoint e `useLogs.ts` mantiene lo stato applicativo. La finestra verifica le capacità prima del montaggio. Le risposte sono collegate all'URL richiesto, per evitare di mostrare dati della selezione precedente quando cambia il dispositivo.
