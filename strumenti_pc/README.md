# Strumento di scansione PC — La Culla

Programma che cerca sul PC i documenti richiesti dallo Studio Dacol (bilancio 2025 / Redditi 2026),
li **copia** nella cartella `LA CULLA – ARCHIVIO` e prepara l'inventario completo del PC per il riordino.

## Regole che il programma rispetta

- **Non sposta, non rinomina, non cancella nulla.** Legge i file e ne fa solo delle copie.
- Non apre portali bancari e non chiede password. Un PDF protetto da password viene segnalato e saltato.
- Scrive soltanto dentro `LA CULLA – ARCHIVIO` (copie + cartella `00_scan` con gli inventari).

## Come si usa (Windows)

1. Scarica questa cartella `strumenti_pc` sul PC (ad esempio sul Desktop).
2. Doppio clic su **`PROVA_SENZA_COPIE.bat`** per una prova: produce inventario e riepilogo senza copiare nulla.
3. Doppio clic su **`AVVIA_SCANSIONE.bat`** per l'esecuzione completa (ricerca, copie, inventario).
4. Alla fine leggi `RIEPILOGO.md` nella cartella `00_scan` dell'archivio (il percorso è scritto a video).

Serve Python 3 (gratuito): se manca, il file `.bat` spiega come installarlo. Per leggere il testo dei PDF
il programma prova a installare da solo la libreria `pypdf`; se non ci riesce, i PDF vengono cercati solo per nome.

## Dove finiscono le copie

- Se sul PC c'è la cartella sincronizzata di Google Drive (`G:\Il mio Drive`, `Google Drive\Il mio Drive`, ...),
  l'archivio viene creato lì: `<Drive>\LA CULLA – ARCHIVIO\` e si sincronizza da solo.
- Altrimenti viene creato in `Documenti\LA CULLA – ARCHIVIO\` e il riepilogo lo dice chiaramente:
  in quel caso va caricato su Google Drive a mano (trascinando la cartella nel Drive).

Struttura creata:

```
LA CULLA – ARCHIVIO/
  00_scan/            inventario_pc.csv, duplicati.csv, proposta_riordino.csv, copie_eseguite.csv, errori.log, RIEPILOGO.md
  01_FISCALE/<anno>/  02_finanziamenti 03_pos_stripe_nexi 04_eviivo 05_fatture_acquisto_xml 06_corrispettivi 07_crypto 08_isa_redditi 10_inventario
  02_CONTRATTI/       affitto_azienda_valgrande noleggi finanziamenti assicurazioni
```

I file copiati mantengono il nome originale con il prefisso `AAAA-MM-GG_` (data presa dal nome del file,
dal tag `<Data>` delle fatture XML, oppure dalla data di modifica).

## Cosa cerca (le 10 voci)

1 criptovalute · 2 finanziamenti · 3 noleggi · 4 Stripe/POS · 5 eviivo · 6 fatture elettroniche e fornitori ·
7 ISA e Redditi · 8 contratti e beni (affitto d'azienda, Valgrande, rogito, inventari) · 9 assicurazioni e contributi ·
10 corrispettivi e magazzino (ZMenu, rimanenze).

Le parole chiave sono in `parole_chiave.json`. I numeri di pratica, contratto e polizza **non** sono in questo
repository (è pubblico): vanno nel file `parole_chiave_private.txt` (una riga per numero, formato `voce;numero`,
es. `2;1234567`), che il programma legge se lo trova accanto allo script oppure in `LA CULLA – ARCHIVIO\00_scan\`.
Il file privato è già pronto su Google Drive in `LA CULLA – ARCHIVIO/00_scan/`.

## Cartelle esaminate

Desktop, Documenti, Download, Immagini, Video, OneDrive, Google Drive locale, export WhatsApp/Telegram e
tutti gli altri dischi collegati (D:, E:, ...). Vengono saltate le cartelle di sistema e programmi
(`AppData`, `Windows`, `Program Files`, cache, `node_modules`, ...) e i file sotto 1 KB che non siano testo o documenti.

## Opzioni avanzate (facoltative)

```
python scan_pc_laculla.py --dry-run            prova senza copie
python scan_pc_laculla.py --solo-inventario    solo inventario (Fase 2)
python scan_pc_laculla.py --no-esterni         non guardare gli altri dischi
python scan_pc_laculla.py --radici D:\Backup E:\  esamina solo queste cartelle
python scan_pc_laculla.py --destinazione "D:\LA CULLA – ARCHIVIO"
python scan_pc_laculla.py --escludi Giochi Film   salta anche queste cartelle
```

## File prodotti in 00_scan

| File | Contenuto |
|---|---|
| `inventario_pc.csv` | percorso, nome, estensione, dimensione, data modifica, SHA1, voce (1–10), parole trovate, data documento |
| `duplicati.csv` | stesso SHA1 presente in più percorsi |
| `proposta_riordino.csv` | per ogni file di lavoro la cartella e il nome proposti (`AAAA-MM-GG_soggetto_descrizione.ext`) — **non applicata** |
| `copie_eseguite.csv` | ogni copia fatta o saltata, con motivo |
| `errori.log` | cartelle non accessibili, PDF protetti, altri problemi |
| `RIEPILOGO.md` | le 10 voci trovato/non trovato, dove sono le copie, numeri, problemi |

I CSV usano il separatore `;` e si aprono direttamente con Excel.
