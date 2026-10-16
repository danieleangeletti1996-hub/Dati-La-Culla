/****************************************************************************************
 * La Culla — Recupero automatico mail "CHIUSURA" ZMenu  (Google Apps Script)
 * --------------------------------------------------------------------------------------
 * Versione 2 (2026-10-16) dello script già presente nell'app La Culla Direzione
 * (app-la-culla/../scripts/gmail-chiusura-AppsScript.gs). Stessa logica, tre aggiunte:
 *   a) setupStorico(): prima esecuzione che recupera TUTTE le chiusure degli ultimi 150 giorni;
 *   b) soloUtili: salva solo i 4 PDF che servono (gli altri 11 sono duplicati o vuoti,
 *      come verificato nell'audit del 2026-06-29); mettere false per salvarli tutti;
 *   c) maxPerRun: un'esecuzione elabora al massimo N giorni operativi, così non supera il
 *      limite di 6 minuti di Apps Script; le mail non ancora etichettate vengono riprese
 *      all'esecuzione successiva (rilanciare setupStorico() finché non dice "0 nuovi").
 *
 * COSA FA ogni esecuzione:
 *   1) cerca le mail con oggetto "CHIUSURA" non ancora etichettate "ZMENU/Importata";
 *   2) legge la DATA OPERATIVA dal corpo ("Report Giornaliero del DD-MM-YYYY");
 *   3) raggruppa per data operativa e gestisce i DOPPIONI delle prove;
 *   4) sceglie la mail PIÙ COMPLETA (più allegati); se due mail hanno allegati diversi
 *      NON decide: manda un avviso email e non salva nulla per quel giorno;
 *   5) salva i PDF in Drive:  La Culla/Chiusure/AAAA-MM-GG/ ;
 *   6) etichetta la mail "ZMENU/Importata" per non rielaborarla.
 *
 * SETUP (una volta, 5 minuti):
 *   - script.google.com → Nuovo progetto → incolla questo file → salva (nome: "La Culla Chiusure").
 *   - Menu funzioni → scegli `setupStorico` → Esegui → autorizza Gmail + Drive + invio email.
 *     Rileggi il log (Visualizza → Log esecuzioni): ripeti finché dice "0 nuovi giorni".
 *   - Trigger (icona orologio a sinistra) → Aggiungi trigger → funzione `eseguiChiusura`,
 *     evento: basato sul tempo, timer giornaliero, fascia 06:00–07:00 → Salva.
 *
 * REGOLE rispettate: data operativa dal report (non la data della mail); mail dopo mezzanotte =
 * giorno precedente; doppioni con stessi dati → 1 sola copia; con dati diversi → avviso.
 ****************************************************************************************/

var CFG = {
  query: 'subject:CHIUSURA newer_than:3d',        // esecuzione giornaliera
  queryStorico: 'subject:CHIUSURA newer_than:150d', // prima esecuzione (recupero storico)
  cartellaRadice: 'La Culla/Chiusure',              // dove salvare in Drive
  labelFatto: 'ZMENU/Importata',
  soloUtili: true,
  pdfUtili: [
    'Report giornaliero.pdf',
    'Report Produzione - Turni di lavoro.pdf',
    'Report Incassi e Pagamenti ADV - Documenti.pdf',
    'Report Incassi e Pagamenti - Sale.pdf'
  ],
  maxPerRun: 40,
  avvisaEmail: Session.getActiveUser().getEmail()
};

function setup(){ eseguiChiusura(); }                 // compatibilità con la versione 1
function setupStorico(){ elabora_(CFG.queryStorico); } // recupero storico: rilanciare finché "0 nuovi"
function eseguiChiusura(){ elabora_(CFG.query); }      // trigger giornaliero

function elabora_(query){
  var label = getOrCreateLabel_(CFG.labelFatto);
  var threads = GmailApp.search(query + ' -label:' + CFG.labelFatto.replace('/','-'));
  var perData = {};   // 'YYYY-MM-DD' -> [ {msg, n, pdfs} ]
  threads.forEach(function(t){
    t.getMessages().forEach(function(m){
      if (!/CHIUSURA/i.test(m.getSubject())) return;
      var iso = dataOperativaDaCorpo_(m.getPlainBody());
      if (!iso) return;                     // se non leggo la data, non tocco nulla
      var pdfs = m.getAttachments().filter(function(a){ return /\.pdf$/i.test(a.getName()); });
      (perData[iso] = perData[iso] || []).push({ msg:m, n:pdfs.length, pdfs:pdfs });
    });
  });

  var giorni = Object.keys(perData).sort();
  var fatti = 0, saltati = 0, conflitti = 0;
  giorni.forEach(function(iso){
    if (fatti >= CFG.maxPerRun) return;
    var gruppo = perData[iso];
    gruppo.sort(function(a,b){ return b.n - a.n; });
    var scelta = gruppo[0];
    var conflitto = gruppo.length > 1 && gruppo[1].n === scelta.n &&
                    firma_(gruppo[1].pdfs) !== firma_(scelta.pdfs);
    if (conflitto){
      conflitti++;
      MailApp.sendEmail(CFG.avvisaEmail, 'La Culla — DOPPIA CHIUSURA CON DIFFERENZE ' + iso,
        'Per il giorno operativo ' + iso + ' ci sono più mail CHIUSURA con allegati diversi.\n' +
        'Non ho scelto da solo: controlla in Gmail e importa a mano quella giusta.');
      return;
    }
    var cartella = getOrCreateFolderPath_(CFG.cartellaRadice + '/' + iso);
    if (cartella.getFiles().hasNext()) {
      // già salvata in una esecuzione precedente: etichetta e basta
      gruppo.forEach(function(g){ g.msg.getThread().addLabel(label); });
      saltati++;
      return;
    }
    scelta.pdfs.forEach(function(a){
      if (CFG.soloUtili && CFG.pdfUtili.indexOf(a.getName()) < 0) return;
      cartella.createFile(a.copyBlob()).setName(a.getName());
    });
    gruppo.forEach(function(g){ g.msg.getThread().addLabel(label); });
    fatti++;
  });
  var rimasti = Math.max(0, giorni.length - fatti - saltati - conflitti);
  Logger.log('Chiusure: ' + fatti + ' nuovi giorni salvati, ' + saltati + ' già presenti, ' +
             conflitti + ' conflitti, ' + rimasti + ' da riprendere alla prossima esecuzione.');
}

/* "Report Giornaliero del 28-06-2026" / "del 28/06/2026" -> "2026-06-28" */
function dataOperativaDaCorpo_(body){
  var m = (body||'').match(/del\s+(\d{2})[-\/](\d{2})[-\/](\d{4})/i);
  return m ? (m[3] + '-' + m[2] + '-' + m[1]) : null;
}
function firma_(pdfs){ return pdfs.map(function(a){return a.getName()+':'+a.getSize();}).sort().join('|'); }

function getOrCreateLabel_(name){ return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name); }
function getOrCreateFolderPath_(path){
  var parts = path.split('/'); var folder = DriveApp.getRootFolder();
  parts.forEach(function(p){
    var it = folder.getFoldersByName(p);
    folder = it.hasNext() ? it.next() : folder.createFolder(p);
  });
  return folder;
}
