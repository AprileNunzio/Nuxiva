# Agente hardware

Il motore identifica dispositivi mediante sysfs, modalias, modules.alias e database locali hwdata. Il catalogo contiene eccezioni e ricette estensibili; non è necessario elencare ogni prodotto per utilizzare i moduli già disponibili nel kernel.

## Responsabilità

- `model.py` e `capabilities.py`: inventario e capacità senza esecuzione di comandi.
- `identify.py`: adattatore sysfs, identificativi e indice dei moduli con invalidazione della cache.
- `catalog.py`, `catalog_validation.py`, `validation.py`: catalogo dichiarativo e controllo degli identificatori.
- `expert.py` e `pipeline.py`: diagnosi, orchestrazione e transazioni di provisioning.
- `execution.py`, `activation.py`, `binding.py`, `modules.py`: esecuzione con timeout, attivazione, riprova del binding e controllo degli errori kernel.
- `repos.py`, `apt_sources.py`, `rpm_repositories.py`, `atomic.py`: repository, scritture atomiche e ripristino APT.
- `dkms.py`: sorgenti esterne fissate a revisioni esatte, compilazione per il kernel corrente e rollback delle sole installazioni possedute dall'operazione.
- `accelerators.py`, `gpu_verification.py`: piani GPU e verifica indipendente dell'accelerazione.
- `managed.py` e `service.py`: inventario persistente dei pacchetti gestiti, monitoraggio e coordinamento delle operazioni.
- `api.py` e `localization.py`: autorizzazione e presentazione multilingua. La tray WebOS consuma `/api/hardware/capabilities`.

## Copertura effettiva

| Area | Comportamento |
| --- | --- |
| USB e PCIe | Classificazione, risoluzione dei moduli e binding effettivo. Le periferiche Thunderbolt che enumerano su PCIe seguono questo percorso. |
| ACPI, I2C, SPI, Thunderbolt | Individuazione degli oggetti che espongono modalias; nessuna invenzione di indirizzi, driver o autorizzazioni Thunderbolt. |
| Debian e Ubuntu | Modifica dei soli mirror riconosciuti, formati sources.list e deb822, componenti appropriati alla distribuzione, backup e ripristino verificato. |
| Fedora e famiglia RHEL | Firmware dai repository della distribuzione; EPEL/builder e RPM Fusion quando necessari. I pacchetti di bootstrap esterni richiedono chiavi già affidabili e verifica della firma. Nessun bypass GPG. |
| Altre distribuzioni | Rilevamento e catalogo disponibili; operazioni non supportate restituiscono un esito esplicito. Gli aggiornamenti parziali Arch sono rifiutati. |
| DKMS | Tre ricette comunitarie Realtek fissate a commit precisi; precedenza ai moduli del kernel. Toolchain e header del kernel corrente. DKMS gestisce le ricompilazioni successive secondo la configurazione della distribuzione. |
| GPU | Driver NVIDIA, firmware/Mesa per AMD e Intel. Su Ubuntu la scelta NVIDIA segue ubuntu-drivers per il dispositivo esatto. Il rendering non implica che CUDA, ROCm o OpenCL siano utilizzabili. |
| Accelerazione NVIDIA | La capacità compute.accelerator richiede driver NVIDIA e risposta nvidia-smi con indirizzo PCI corrispondente. |

## Ciclo operativo

Il monitor controlla l'inventario ogni quattro secondi. Diagnosi e accessi sysfs pesanti non bloccano l'event loop. Le operazioni sono serializzate e i duplicati per dispositivo sono rifiutati. La disconnessione annulla il provisioning; timeout e cancellazione eliminano il processo avviato e, su Linux, il relativo gruppo.

Un dispositivo passa a pronto solo dopo i controlli previsti: installazione riuscita, attivazione riuscita, dispositivo ancora presente e driver agganciato; Wi-Fi/Ethernet richiedono anche un'interfaccia. I firmware noti devono essere presenti. Le capacità vengono ritirate durante la configurazione e aggiornate al termine dell'operazione.

Il registro `hardware_managed.json` risiede nella directory di stato configurata e contiene identificativi tecnici, pacchetti e timestamp, senza credenziali o numeri seriali. Ogni 24 ore vengono ricontrollati i dispositivi gestiti con pacchetti associati. Si aggiornano i loro pacchetti, non l'intero sistema. Le GPU con sessione grafica attiva richiedono conferma amministrativa per aggiornamenti che possono interferire con il display. Le operazioni manuali richiedono autenticazione admin e la protezione delle richieste già prevista da Nuxiva.

## Limiti e sicurezza

Una revisione Git immutabile garantisce l'identità dei sorgenti selezionati, non costituisce un audit completo del loro codice. Le ricette esterne sono parte della base di fiducia del prodotto. Non vengono eseguite ricette generate da un LLM o recuperate arbitrariamente dal web.

Il broker non cancella sorgenti preesistenti, non usa installazioni DKMS forzate e non rimuove registrazioni che non ha creato. La sostituzione di una ricetta con la stessa versione ma revisione diversa richiede una migrazione esplicita. Con Secure Boot attivo, il percorso sorgenti viene rifiutato se non è disponibile il flusso di firma supportato: Secure Boot non viene disabilitato e le chiavi non vengono iscritte automaticamente.

Il rollback APT ripristina soltanto le modifiche dell'operazione corrente e rifiuta di sovrascrivere interventi amministrativi concorrenti. Non disinstalla pacchetti condivisi né annulla automaticamente tutte le modifiche RPM. I riavvii non vengono eseguiti automaticamente.

Il controllo degli errori kernel può scaricare un modulo appena caricato e metterlo in quarantena temporanea se il sistema resta operativo. Non può impedire o recuperare un kernel panic che arresta la macchina. Non vengono rimossi moduli già presenti prima dell'operazione e non vengono scollegate altre schede per ricaricare un driver condiviso.

Non esiste una garanzia di compatibilità con ogni dispositivo: occorrono driver, firmware e licenze compatibili con kernel, architettura e distribuzione. Firmware del produttore, sensori senza modalias, hardware proprietario non documentato, stack ROCm/CUDA completi e una matrice cloud globale non sono implementati da questa estensione.

## Riferimenti

- [Binding dei driver Linux](https://docs.kernel.org/driver-api/driver-model/binding.html)
- [DKMS](https://github.com/dkms-project/dkms)
- [Configurazione RPM Fusion](https://rpmfusion.org/Configuration)
