# Archivio unico La Culla (Drive = master, PC = copia sincronizzata)

Principi: un solo posto (Google Drive, cartella `LA CULLA – ARCHIVIO`, sincronizzata sul PC con "Google Drive per desktop"); stessa struttura ovunque; nomi file `AAAA-MM-GG_soggetto_descrizione.ext`; `00_INDICE.md` in cima dice cosa sta dove; niente cancellazioni, solo spostamenti registrati.

```
LA CULLA – ARCHIVIO/
  00_INDICE.md
  00_scan/                     inventario del PC, duplicati, proposta di riordino, log spostamenti
  01_FISCALE/<anno>/
      01_estratti_conto        02_finanziamenti        03_pos_stripe_nexi      04_fatture_vendita
      05_fatture_acquisto_xml  06_corrispettivi        07_crypto               08_isa_redditi
      09_commercialista        10_inventario           99_da_inviare_studio
  02_CONTRATTI/
      affitto_azienda_valgrande  locazioni  noleggi  finanziamenti  assicurazioni  utenze  fornitori_servizi
  03_PERSONALE/<anno>/
      assunzioni  cedolini  sicurezza_haccp_antincendio
  04_STRUTTURE/  bnb  ristorante  rifugio   (autorizzazioni, SCIA, planimetrie, manutenzioni)
  05_ATTREZZATURE/  beni_in_affitto  beni_propri  noleggi  foto_video/<AAAA-MM>
  06_FORNITORI/<fornitore>/  listini  ordini
  07_OSPITI/<anno>/          export Beddy / eviivo / Booking (dati personali: accesso ristretto)
  08_MENU_MARKETING/  menu  carta_vini  foto  canva
  09_PRIVATO/                separato dal business
  99_INBOX_DA_SMISTARE/      tutto ciò che arriva e non ha ancora una casa
```

## Fasi
1. **Scansione** (card "Scansiona il PC"): inventario e copie su Drive dei documenti fiscali; nessuno spostamento. Output in `00_scan/`.
2. **Riordino** (card "Riordina il PC", dopo il sì di Daniele su `proposta_riordino.csv`): spostamenti nella struttura, `log_spostamenti.csv` con percorso prima/dopo, nessuna cancellazione, aggiornamento `00_INDICE.md`.
3. **Manutenzione**: routine mensile che archivia da Gmail su Drive le fatture ricorrenti (eviivo, Stripe, Wörndle, PEC Unicomm, Booking, Nexi, bollette) nella cartella dell'anno; tutto il resto va in `99_INBOX_DA_SMISTARE` e si smista una volta al mese.

## Regole nomi
- Data all'inizio nel formato ISO: `2025-12-15_eviivo_fattura_EV00203811.pdf`
- Soggetto = chi ha emesso o a cosa si riferisce: `findomestic`, `santander`, `stripe`, `unicomm`, `avepa`, `isa`.
- Niente spazi doppi, niente "definitivo2", niente "nuovo": la versione buona è quella senza suffisso; le vecchie vanno in una sottocartella `_vecchie`.
