# Fase 0 — Cosa deve fare Daniele (circa 20 minuti)

Tre passaggi, una volta sola. Dopo questi, Claude lavora dal cloud sull'app e la Routine
giornaliera può partire. Ordine consigliato: A → B → C.

---

## A) App "La Culla Direzione" su GitHub privato (10 minuti)

Il repo dell'app sta solo sul PC (`C:\Users\danie\Desktop\menu\code`). Serve una copia
privata su GitHub: backup fuori dal PC (consigliato dal runbook `docs/BACKUP_GIT_RUNBOOK.md`
§2 dell'app) e accesso per Claude dal cloud.

1. Su github.com → **New repository** → nome `la-culla-direzione` → **Private** → NON
   spuntare "Add a README" → Create.
   (Claude ha provato a crearlo dal cloud: la GitHub App non ha il permesso, va fatto a mano.)
2. Apri PowerShell (o il terminale di Claude Code) nella cartella dell'app ed esegui,
   una riga alla volta:

   ```powershell
   cd C:\Users\danie\Desktop\menu\code
   git status --short
   git ls-files dati-privati
   git ls-files | findstr /i "gmail-oauth.local laculla-backup .zip"
   ```

   Atteso: `git status --short` vuoto (tree pulito), le altre due righe **vuote**
   (nessun dato privato tracciato). Se escono file, FERMATI e mandami l'output.

3. Collega e pubblica:

   ```powershell
   git remote add origin https://github.com/danieleangeletti1996-hub/la-culla-direzione.git
   git push -u origin main
   ```

   Al primo push GitHub chiede il login (finestra del browser).

4. Dai accesso alla GitHub App di Claude al nuovo repo:
   github.com → Settings → Applications → **Claude** → Configure → Repository access →
   aggiungi `la-culla-direzione` → Save.

5. Scrivimi "push fatto": aggiungo il repo alla sessione e inizio la Fase 1.

Regola da oggi: sul PC fai `git pull` prima di aprire una sessione Claude Code locale e
`git push` quando chiudi. Un solo agente alla volta sull'app (regola già del progetto).

## B) Dati-La-Culla privato (1 minuto)

github.com/danieleangeletti1996-hub/Dati-La-Culla → Settings → in fondo "Danger Zone" →
**Change repository visibility** → Private → conferma scrivendo il nome del repo.

Finché resta pubblico Claude non committa nessun numero (incassi, coperti, ecc.), solo codice.
Nota: la **PR #1** (strumenti fiscali: parser fatture XML, export Stripe, scansione PC) è
stata verificata il 16/10/2026 con i suoi 4 test tutti verdi ed è stata unita in `main`.

## C) Apps Script per le email CHIUSURA (5 minuti)

Serve perché il connettore Gmail di Claude non scarica gli allegati. Lo script copia ogni
notte i PDF ZMenu su Drive in `La Culla/Chiusure/AAAA-MM-GG/`. È la versione 2 dello script
già scritto a giugno nell'app (`scripts/gmail-chiusura-AppsScript.gs`): stessa logica, in più
recupera lo storico da luglio, salva solo i 4 PDF utili e lavora a blocchi di 40 giorni.

1. Apri **script.google.com** con l'account `danieleangeletti1996@gmail.com` (quello che
   riceve le email CHIUSURA) → **Nuovo progetto**.
2. Cancella il contenuto di `Codice.gs` e incolla tutto il file
   `scripts/gmail/SalvaChiusure.gs` di questo repo → salva (icona dischetto) → rinomina il
   progetto "La Culla Chiusure".
3. In alto, nel menu a tendina delle funzioni scegli **setupStorico** → **Esegui**.
   Google chiede l'autorizzazione (Gmail, Drive, invio email): "Avanzate" → "Vai a La Culla
   Chiusure (non sicuro)" → Consenti. È il TUO script nel TUO account: nessun terzo.
4. Apri "Log esecuzioni": l'ultima riga dice quanti giorni ha salvato e quanti restano.
   Rilancia **setupStorico** finché dice `0 da riprendere`. (Circa 100 giorni da luglio:
   3 esecuzioni.)
5. A sinistra icona **orologio (Trigger)** → **Aggiungi trigger** → funzione
   `eseguiChiusura` → origine evento "Basato sul tempo" → "Timer giornaliero" → fascia
   **06:00–07:00** → Salva.
6. Verifica su Drive: cartella `La Culla/Chiusure/2026-10-15/` con `Report giornaliero.pdf`.
   In Gmail le email elaborate hanno l'etichetta `ZMENU/Importata`.

Se arriva un'email "DOPPIA CHIUSURA CON DIFFERENZE": per quel giorno ci sono due chiusure
diverse (es. una prova). Lo script non sceglie: importa a mano quella giusta nell'app.

---

## Cosa succede dopo

- **Fase 1 (Claude, cloud)**: nell'app, import di tutte le chiusure dalla cartella Drive con
  un clic, alert "chiusura mancante" con il perché, registrazione delle tue decisioni del
  16/10 nei file di governo del progetto. Tutto su branch, test completi, checkpoint.
- **Fase 2 (Claude, cloud)**: Routine ogni mattina alle 7:40: legge i PDF da Drive, aggiorna
  `data/` in questo repo (privato), produce i consigli con i perché e pubblica il riepilogo
  privato per il telefono.
