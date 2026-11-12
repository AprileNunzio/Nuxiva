# Autorizzazioni WebOS, API e MCP

Le autorizzazioni devono essere verificate dal server. Nascondere un comando nella UI non concede né revoca un permesso.

## Supervisor e applicazioni

`features/authz/access_control.py` collega i ruoli degli account alla policy di rischio già usata dagli strumenti. Gli account sono conservati in `STATE_DIR/authz/accounts.json`, con ruolo e nodi assegnati. Un file non leggibile o non valido blocca l'accesso: non ripristina implicitamente i privilegi.

Le API che usano `require_admin` richiedono `api.admin` come valore predefinito. Per consentire un accesso più specifico, una rotta dichiara `openapi_extra={"x-nuxiva-capabilities": ["logs.read"]}`. Una rotta che opera su un dispositivo deve inoltre chiamare `require_permission(user, capability, node_id)` dopo aver risolto il dispositivo. Autenticazione e protezione delle richieste di modifica restano obbligatorie.

L'accesso alle API legacy non viene esteso ai ruoli limitati. La migrazione verso permessi specifici richiede un controllo della risorsa e test di accesso negato per ogni rotta. Le API pubbliche, locali e di abbinamento hanno contratti distinti e richiedono una revisione separata: questa base non costituisce una certificazione di copertura di ogni endpoint.

Il contratto predisposto per il WebOS espone `/api/authz/access`. Le applicazioni dichiarano `manifest.capabilities`; la finestra verifica i permessi prima di montare il contenuto. Le API restano l'autorità finale. La nuova applicazione Log, in lavorazione, deve verificare separatamente lettura, esportazione e nodo assegnato.

## MCP

I token includono un ruolo e un elenco opzionale `allowed_tools` con pattern. Un elenco vuoto non consente strumenti; l'assenza conserva la compatibilità con la selezione esistente. La selezione effettiva interseca ruolo, policy di rischio, ambito e limitazioni del token. Il runner riceve il principal del token, mai automaticamente `system`. Le azioni delicate conservano la conferma esplicita.

Il flag `risky` non supera i limiti del ruolo. Un token amministratore richiede una creazione esplicita con `risky=true`. Risorse e prompt richiedono un permesso distinto. I token esistenti mantengono la classificazione precedente durante la migrazione; revocarli e riemetterli permette di restringerne il ruolo e gli strumenti.

## Core

Le API di amministrazione RBAC richiedono un token verificato con un attore utente esplicito e `rbac:manage` nella matrice del Core. Il solo subject di un token dispositivo non identifica un amministratore. I token OPERATOR di scambio locale non possono modificare gli account. La delega fra sessione Supervisor e identità Core deve essere autenticata: non aggiungere un fallback basato sul nome dichiarato dal client.

## Verifiche

`test_access_control.py` copre ruoli, ambiti dei nodi, policy corrotte, API senza classificazione, rimozione dei propri privilegi e token MCP. `test_rbac_authorization.py` copre autenticazione delle rotte Core, impersonificazione tramite subject e permesso di amministrazione. I test della nuova applicazione Log saranno pubblicati insieme alla relativa funzionalità.
