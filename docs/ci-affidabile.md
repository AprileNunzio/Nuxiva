# CI affidabile / Reliable CI

## Perché i commit risultavano rossi / Why commits looked red

IT: nei 40 run più recenti su `main`, 15 erano **annullati** (un nuovo push o la ricompilazione automatica della dist 8080 annullava il run in corso) e 7 erano errori veri, tutti già corretti da commit successivi: import inutilizzato, file Rust oltre 500 righe, test NVR con data fissa che scade, marcatori di conflitto lasciati in `web/display/language/*.json`. Un test (`test_gait`) era instabile con Python 3.12+, cinque test usavano la rete esterna.

EN: of the 40 latest runs on `main`, 15 were **cancelled** (a new push or the automatic 8080 dist rebuild cancelled the running one) and 7 were real errors, all fixed by later commits: unused import, Rust file over 500 lines, NVR test with a fixed date that expires, conflict markers left in `web/display/language/*.json`. One test (`test_gait`) was unstable on Python 3.12+, five tests used the external network.

## Metodo / Method

1. **Prima del push** / before pushing: `bash scripts/dev/install_hooks.sh` una volta sola (una volta per clone). L'hook `.githooks/pre-push` esegue `scripts/ci/check.sh fast`, che riproduce i job della CI: ramo allineato a `origin/main` e albero pulito, nota in `changelog/` per ogni commit, limite 500 righe, marcatori di conflitto, pyflakes e compilazione Python, sintassi shell e JS, Rust (fmt sempre, clippy e test se cambia `native/`), build web (se cambia `client_web/`), test Python e del kernel. `scripts/ci/check.sh full` esegue tutto. Dipendenze: Python con `pyflakes` e i requirements dell'installer, Rust, Node.
2. **Se il ramo è indietro** / if the branch is behind: `git pull --rebase origin main`, poi ripeti i controlli. Più thread pubblicano su main: fetch e rebase subito prima di ogni push.
3. **In CI** / in CI: ogni commit su `main` ha il suo run, mai annullato da un altro push (la concurrency annulla solo le pull request). Il job `ci-status` dà un riepilogo unico e distingue **fallito** da **annullato**. Un run notturno fa emergere i test che scadono con il calendario.
4. **Test rossi** / red tests: `scripts/ci/unit.py` rilancia ogni test fallito da solo (2 volte) e lo classifica: *vero* (fallisce sempre), *ordine* (passa da solo, dipende da stato condiviso), *instabile* (a volte passa). Elenca anche i test che aprono connessioni verso reti esterne (`--network report`, oppure `enforce` per vietarle). Non esiste quarantena silenziosa: un test instabile resta rosso finché non viene corretto.
5. **Test deterministici**: niente data fissa nel futuro, niente rete reale, orologio o `now` passati come parametro.
6. **Dopo il push** / after the push: verifica che il run di CI del proprio commit sia verde prima di dichiarare finito. Un rosso "annullato" non è un successo: riesegui.

`NUXIVA_SKIP_PREPUSH=1` salta l'hook solo in emergenza e va dichiarato nel messaggio del commit.
