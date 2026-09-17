#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scansione PC "La Culla" - ricerca documenti per lo Studio Dacol, copia in archivio, inventario.

REGOLE: solo LETTURA e COPIE. Questo programma non sposta, non rinomina e non cancella
nessun file esistente. Le uniche scritture avvengono dentro la cartella di destinazione
"LA CULLA – ARCHIVIO" (copie dei documenti trovati e i file di inventario in 00_scan).

Uso tipico (Windows): doppio clic su AVVIA_SCANSIONE.bat (oppure PROVA_SENZA_COPIE.bat).
Uso avanzato:  python scan_pc_laculla.py [--dry-run] [--solo-inventario] [--profilo DIR]
                                         [--radici DIR ...] [--destinazione DIR] [--no-esterni]

Richiede solo la libreria standard di Python (>= 3.8). Per leggere il testo dei PDF usa
"pypdf" se installato (prova a installarlo da solo con pip; se non riesce, salta il
contenuto dei PDF e cerca solo nel nome).
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import string
import subprocess
import sys
import time
import traceback
import unicodedata
import zipfile

# --------------------------------------------------------------------------------------
# Costanti
# --------------------------------------------------------------------------------------

VERSIONE = "1.0"
NOME_ARCHIVIO = "LA CULLA – ARCHIVIO"   # trattino lungo (en dash)
CARTELLA_SCAN = "00_scan"
ANNO_RIFERIMENTO = 2025

# Sottocartelle richieste dalla Fase 1 (create sempre)
SOTTOCARTELLE_FASE1 = [
    "01_FISCALE/2025/02_finanziamenti",
    "01_FISCALE/2025/03_pos_stripe_nexi",
    "01_FISCALE/2025/04_eviivo",
    "01_FISCALE/2025/05_fatture_acquisto_xml",
    "01_FISCALE/2025/06_corrispettivi",
    "01_FISCALE/2025/07_crypto",
    "01_FISCALE/2025/08_isa_redditi",
    "01_FISCALE/2025/10_inventario",
    "02_CONTRATTI/affitto_azienda_valgrande",
    "02_CONTRATTI/noleggi",
    "02_CONTRATTI/finanziamenti",
    "02_CONTRATTI/assicurazioni",
]

# Destinazione delle copie per voce. "{anno}" viene sostituito con l'anno del documento
# (dal nome file, altrimenti data di modifica) solo per le voci fiscali; i contratti non hanno anno.
DESTINAZIONE_VOCE = {
    1: "01_FISCALE/{anno}/07_crypto",
    2: "01_FISCALE/{anno}/02_finanziamenti",
    3: "02_CONTRATTI/noleggi",
    4: "01_FISCALE/{anno}/03_pos_stripe_nexi",
    5: "01_FISCALE/{anno}/04_eviivo",
    6: "01_FISCALE/{anno}/05_fatture_acquisto_xml",
    7: "01_FISCALE/{anno}/08_isa_redditi",
    8: "02_CONTRATTI/affitto_azienda_valgrande",
    9: "02_CONTRATTI/assicurazioni",
    10: "01_FISCALE/{anno}/06_corrispettivi",
}
# Eccezioni dentro una voce (parola nel nome/contenuto -> destinazione diversa)
DESTINAZIONE_ECCEZIONI = [
    (8, ("inventario", "elenco beni", "cespiti", "attrezzature"), "01_FISCALE/{anno}/10_inventario"),
    (10, ("rimanenze", "giacenze", "magazzino", "inventario"), "01_FISCALE/{anno}/10_inventario"),
    (9, ("avepa", "contributo"), "01_FISCALE/{anno}/02_finanziamenti"),
]

CARTELLE_ESCLUSE = {
    "appdata", "$recycle.bin", "system volume information", "node_modules", ".git", "__pycache__",
    ".cache", "cache", "caches", "cache2", "windows", "program files", "program files (x86)",
    "programdata", ".venv", "venv", "site-packages", ".gradle", ".npm", ".nuget", ".m2", "temp", "tmp",
    "$windows.~bt", "$windows.~ws", "windows.old", "recovery", "perflogs", "msocache", "intel", "amd",
    "nvidia", "drivers", ".vscode", ".idea", ".android", ".dotnet", "onedrivetemp", "library",
    ".trash", ".thumbnails", "thumbnails", "steam", "steamapps", "epic games", "riot games",
    "microsoft", "packages", "windowsapps", "obj", "bin", "build", "dist", "target", ".config",
}
ESTENSIONI_ESCLUSE = {
    ".exe", ".dll", ".msi", ".sys", ".lnk", ".tmp", ".dat", ".bin", ".iso", ".jar", ".class", ".pyc",
    ".pyd", ".o", ".obj", ".lib", ".so", ".dylib", ".url", ".log", ".db", ".db-wal", ".db-shm", ".pak",
    ".pkg", ".ttf", ".otf", ".fon", ".ico", ".cur", ".manifest", ".cab", ".inf", ".cat", ".etl",
    ".evtx", ".pf", ".idx", ".chk", ".part", ".crdownload", ".ini", ".cfg", ".plist", ".sqlite",
    ".sqlite3", ".ldb", ".apk", ".ipa", ".deb", ".rpm", ".vdi", ".vmdk", ".ova", ".wim", ".esd",
    ".swf", ".woff", ".woff2", ".eot", ".ds_store",
}
NOMI_FILE_ESCLUSI = {"thumbs.db", "desktop.ini", ".ds_store", "ntuser.dat", "iconcache.db"}

EST_TESTO = {".txt", ".csv", ".tsv", ".md", ".json", ".html", ".htm", ".eml", ".xml", ".rtf", ".mht",
             ".vcf", ".ics", ".yml", ".yaml"}
EST_OFFICE_ZIP = {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".docm", ".xlsm"}
EST_OFFICE_BIN = {".doc", ".xls", ".ppt"}
EST_PDF = {".pdf"}
EST_P7M = {".p7m"}
EST_IMMAGINI = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
EST_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv"}
EST_ARCHIVI = {".zip", ".rar", ".7z"}
EST_LAVORO = (EST_TESTO | EST_OFFICE_ZIP | EST_OFFICE_BIN | EST_PDF | EST_P7M | EST_IMMAGINI
              | EST_VIDEO | EST_ARCHIVI | {".msg", ".numbers", ".pages", ".key"})

LIMITE_CONTENUTO_BYTES = 2 * 1024 * 1024      # quanti byte leggere dai file di testo
LIMITE_TESTO_ESTRATTO = 3 * 1024 * 1024       # quanti caratteri conservare per la ricerca
PAGINE_PDF_MAX = 20

# --------------------------------------------------------------------------------------
# Utilità
# --------------------------------------------------------------------------------------

def is_windows():
    return os.name == "nt"


def percorso_lungo(p):
    """Su Windows aggiunge il prefisso \\\\?\\ ai percorsi lunghi per evitare errori."""
    if is_windows() and len(p) > 240 and not p.startswith("\\\\?\\"):
        p = os.path.abspath(p)
        if p.startswith("\\\\"):
            return "\\\\?\\UNC\\" + p[2:]
        return "\\\\?\\" + p
    return p


def normalizza(testo):
    """minuscolo, senza accenti, apostrofi e simboli -> spazio."""
    if not testo:
        return ""
    testo = unicodedata.normalize("NFKD", testo)
    testo = "".join(c for c in testo if not unicodedata.combining(c))
    testo = testo.lower()
    testo = testo.replace("’", " ").replace("'", " ").replace("`", " ")
    return testo


def slug(testo, max_len=60):
    t = normalizza(testo)
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t[:max_len].strip("_") or "file"


def fmt_dim(n):
    for unita in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unita == "TB":
            return ("%d %s" % (n, unita)) if unita == "B" else ("%.1f %s" % (n, unita))
        n /= 1024.0
    return "%d B" % n


def sha1_file(path, limite_bytes):
    h = hashlib.sha1()
    with open(percorso_lungo(path), "rb") as f:
        letti = 0
        while True:
            blocco = f.read(1024 * 1024)
            if not blocco:
                break
            h.update(blocco)
            letti += len(blocco)
            if limite_bytes and letti > limite_bytes:
                return ""  # troppo grande: niente hash
    return h.hexdigest()


RE_DATA_ISO = re.compile(r"(?<!\d)(20\d{2})[-_. ]?(0[1-9]|1[0-2])[-_. ]?(0[1-9]|[12]\d|3[01])(?!\d)")
RE_DATA_IT = re.compile(r"(?<!\d)(0?[1-9]|[12]\d|3[01])[-_./ ](0?[1-9]|1[0-2])[-_./ ](20\d{2})(?!\d)")
RE_ANNO_MESE = re.compile(r"(?<!\d)(20\d{2})[-_.](0[1-9]|1[0-2])(?!\d)")
MESI_IT = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7,
           "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12}
RE_MESE_ANNO = re.compile(r"\b(" + "|".join(MESI_IT) + r")[ _-]*(20\d{2})\b")


RE_ANNO_NOME = re.compile(r"(?<!\d)(20[12]\d)(?!\d)")


def anno_da_nome(nome):
    """Anno esplicito nel nome file (es. 'Estratto 2025.csv'), altrimenti None."""
    anni = [int(a) for a in RE_ANNO_NOME.findall(nome) if 2015 <= int(a) <= 2035]
    return anni[-1] if anni else None


RE_DATA_XML = re.compile(r"<data>\s*(20\d{2})-(\d{2})-(\d{2})\s*</data>")


def data_da_xml(testo):
    """Data documento dal tag <Data> della fattura elettronica (testo gia' normalizzato o no)."""
    m = RE_DATA_XML.search(testo.lower())
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "contenuto"
        except ValueError:
            pass
    return None, ""


def data_da_nome(nome):
    """Ritorna (date, 'nome') se nel nome file c'e' una data plausibile, altrimenti (None, '')."""
    n = normalizza(nome)
    for regex, ordine in ((RE_DATA_ISO, "ymd"), (RE_DATA_IT, "dmy")):
        m = regex.search(n)
        if m:
            try:
                if ordine == "ymd":
                    d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                else:
                    d = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                if 2000 <= d.year <= 2035:
                    return d, "nome"
            except ValueError:
                pass
    m = RE_ANNO_MESE.search(n)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), 1), "nome(mese)"
        except ValueError:
            pass
    m = RE_MESE_ANNO.search(n)
    if m:
        return dt.date(int(m.group(2)), MESI_IT[m.group(1)], 1), "nome(mese)"
    return None, ""


# --------------------------------------------------------------------------------------
# Parole chiave
# --------------------------------------------------------------------------------------

def regex_da_parola(parola):
    """'ford credit' -> \\bford\\W+credit\\b sul testo normalizzato."""
    p = normalizza(parola)
    pezzi = [re.escape(x) for x in re.split(r"[^a-z0-9]+", p) if x]
    if not pezzi:
        return None
    corpo = r"\W+".join(pezzi)
    return re.compile(r"(?<![a-z0-9])" + corpo + r"(?![a-z0-9])")


class Voce:
    def __init__(self, numero, nome):
        self.numero = numero
        self.nome = nome
        self.forti = []      # (parola, regex)
        self.generiche = []  # (parola, regex)
        self.pattern = []    # (testo, regex)

    def aggiungi(self, tipo, parola):
        if tipo == "pattern":
            try:
                self.pattern.append((parola, re.compile(parola)))
            except re.error:
                pass
            return
        rx = regex_da_parola(parola)
        if rx is None:
            return
        (self.forti if tipo == "forti" else self.generiche).append((parola, rx))


def carica_voci(cartella_script, cartelle_private):
    """Legge parole_chiave.json e, se esiste, parole_chiave_private.txt (righe 'voce;parola')."""
    voci = {}
    percorso_json = os.path.join(cartella_script, "parole_chiave.json")
    with open(percorso_json, "r", encoding="utf-8") as f:
        dati = json.load(f)
    for num, blocco in dati["voci"].items():
        v = Voce(int(num), blocco.get("nome", "voce %s" % num))
        for tipo in ("forti", "generiche", "pattern"):
            for parola in blocco.get(tipo, []):
                v.aggiungi(tipo, parola)
        voci[int(num)] = v
    privati_letti = []
    for cartella in cartelle_private:
        p = os.path.join(cartella, "parole_chiave_private.txt")
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    for riga in f:
                        riga = riga.strip()
                        if not riga or riga.startswith("#"):
                            continue
                        if ";" in riga:
                            num, parola = riga.split(";", 1)
                        elif ":" in riga:
                            num, parola = riga.split(":", 1)
                        else:
                            continue
                        num = num.strip()
                        parola = parola.strip()
                        if num.isdigit() and int(num) in voci and parola:
                            voci[int(num)].aggiungi("forti", parola)
                privati_letti.append(p)
            except OSError:
                pass
    return voci, privati_letti


RE_CSV_CRYPTO = re.compile(r"(date|time|timestamp)[^\n]{0,200}(pair|asset|coin|currency|symbol|market)[^\n]{0,200}(amount|quantity|qty|total|price)", re.I)


def classifica(voci, nome_file, testo, estensione):
    """
    Ritorna (voce_primaria o None, elenco voci secondarie, parole trovate, punteggio).
    Nel nome basta una parola qualunque (forte o generica). Nel contenuto serve una parola forte
    o un pattern, oppure almeno due parole generiche diverse.
    """
    nome_n = normalizza(nome_file)
    testo_n = normalizza(testo) if testo else ""
    risultati = []  # (punteggio, numero_voce, parole)
    for num, v in voci.items():
        punti = 0
        trovate = []
        for parola, rx in v.forti:
            if rx.search(nome_n):
                punti += 10
                trovate.append("nome:" + parola)
            elif testo_n and rx.search(testo_n):
                punti += 5
                trovate.append("testo:" + parola)
        for parola, rx in v.pattern:
            if rx.search(nome_n):
                punti += 10
                trovate.append("nome:/" + parola + "/")
            elif testo_n and rx.search(testo_n):
                punti += 5
                trovate.append("testo:/" + parola + "/")
        gen_nome = [p for p, rx in v.generiche if rx.search(nome_n)]
        gen_testo = [p for p, rx in v.generiche if testo_n and rx.search(testo_n)]
        if gen_nome:
            punti += 3
            trovate.extend("nome~:" + p for p in gen_nome)
        if len(set(gen_testo)) >= 2:
            punti += 2
            trovate.extend("testo~:" + p for p in gen_testo[:3])
        elif gen_testo and punti > 0:
            trovate.extend("testo~:" + p for p in gen_testo[:2])
        if num == 1 and estensione in (".csv", ".xlsx", ".xls") and testo_n and RE_CSV_CRYPTO.search(testo_n):
            punti += 6
            trovate.append("testo:intestazione-csv-crypto")
        if punti > 0:
            risultati.append((punti, num, trovate))
    if not risultati:
        return None, [], [], 0
    risultati.sort(key=lambda r: (-r[0], r[1]))
    primaria = risultati[0]
    secondarie = [r[1] for r in risultati[1:] if r[0] >= 5]
    return primaria[1], secondarie, primaria[2], primaria[0]


# --------------------------------------------------------------------------------------
# Estrazione contenuto
# --------------------------------------------------------------------------------------

class Estrattore:
    def __init__(self, usa_pypdf, limite_mb):
        self.limite = limite_mb * 1024 * 1024
        self.pypdf = None
        self.pdf_protetti = []
        self.errori = []
        if usa_pypdf:
            try:
                import pypdf  # noqa
                self.pypdf = pypdf
            except (KeyboardInterrupt, SystemExit):
                raise
            except BaseException:  # anche errori interni di librerie (es. 'cryptography' rotta)
                self.pypdf = None

    def testo(self, path, estensione, dimensione):
        """Ritorna (testo, nota). Non solleva mai eccezioni."""
        if dimensione > self.limite:
            return "", "contenuto saltato (file > %d MB)" % (self.limite // (1024 * 1024))
        try:
            if estensione in EST_TESTO:
                return self._testo_semplice(path), ""
            if estensione in EST_OFFICE_ZIP:
                return self._office_zip(path), ""
            if estensione in EST_OFFICE_BIN:
                return self._stringhe_binarie(path), ""
            if estensione in EST_PDF:
                return self._pdf(path)
            if estensione in EST_P7M:
                return self._p7m(path), ""
            if estensione == ".msg":
                return self._stringhe_binarie(path), ""
        except zipfile.BadZipFile:
            return "", "archivio zip danneggiato"
        except Exception as e:  # pragma: no cover
            self.errori.append("%s: %s" % (path, e))
            return "", "errore lettura contenuto: %s" % e
        return "", ""

    def _leggi_bytes(self, path, n=LIMITE_CONTENUTO_BYTES):
        with open(percorso_lungo(path), "rb") as f:
            return f.read(n)

    def _testo_semplice(self, path):
        b = self._leggi_bytes(path)
        if b.startswith(b"\xff\xfe") or b.startswith(b"\xfe\xff"):
            return b.decode("utf-16", errors="ignore")
        t = b.decode("utf-8", errors="ignore")
        if "\x00" in t[:4000]:
            t = b.decode("utf-16-le", errors="ignore")
        return t[:LIMITE_TESTO_ESTRATTO]

    def _office_zip(self, path):
        pezzi = []
        totale = 0
        with zipfile.ZipFile(percorso_lungo(path)) as z:
            for info in z.infolist():
                n = info.filename.lower()
                if not n.endswith(".xml"):
                    continue
                if not (n.startswith("word/") or n.startswith("xl/sharedstrings") or n.startswith("xl/worksheets/")
                        or n.startswith("ppt/slides/") or n == "content.xml" or n.startswith("docprops/")):
                    continue
                if info.file_size > 20 * 1024 * 1024:
                    continue
                try:
                    dati = z.read(info)
                except RuntimeError as e:  # zip cifrato
                    raise RuntimeError("file protetto da password") from e
                testo = re.sub(r"<[^>]+>", " ", dati.decode("utf-8", errors="ignore"))
                pezzi.append(testo)
                totale += len(testo)
                if totale > LIMITE_TESTO_ESTRATTO:
                    break
        return " ".join(pezzi)[:LIMITE_TESTO_ESTRATTO]

    def _stringhe_binarie(self, path):
        """Per .doc/.xls/.ppt/.msg: estrae le sequenze leggibili (ASCII e UTF-16LE)."""
        b = self._leggi_bytes(path, 6 * 1024 * 1024)
        ascii_ = " ".join(m.decode("latin-1") for m in re.findall(rb"[\x20-\x7e\xa0-\xff]{4,}", b))
        utf16 = " ".join(m.decode("utf-16-le", errors="ignore") for m in re.findall(rb"(?:[\x20-\x7e]\x00){4,}", b))
        return (ascii_ + " " + utf16)[:LIMITE_TESTO_ESTRATTO]

    def _pdf(self, path):
        if self.pypdf is None:
            return "", "testo PDF non letto (pypdf assente)"
        try:
            lettore = self.pypdf.PdfReader(percorso_lungo(path))
            if lettore.is_encrypted:
                try:
                    esito = lettore.decrypt("")
                except Exception:
                    esito = 0
                if not esito:
                    self.pdf_protetti.append(path)
                    return "", "PDF PROTETTO DA PASSWORD"
            pezzi = []
            for i, pagina in enumerate(lettore.pages):
                if i >= PAGINE_PDF_MAX:
                    break
                try:
                    pezzi.append(pagina.extract_text() or "")
                except Exception:
                    continue
            return " ".join(pezzi)[:LIMITE_TESTO_ESTRATTO], ""
        except Exception as e:
            msg = str(e).lower()
            if "password" in msg or "encrypt" in msg or "crypt" in msg:
                self.pdf_protetti.append(path)
                return "", "PDF PROTETTO DA PASSWORD"
            return "", "PDF non leggibile (%s)" % e.__class__.__name__

    def _p7m(self, path):
        b = self._leggi_bytes(path, 4 * 1024 * 1024)
        i = b.find(b"<?xml")
        if i >= 0:
            return b[i:].decode("utf-8", errors="ignore")[:LIMITE_TESTO_ESTRATTO]
        try:
            import base64
            dec = base64.b64decode(re.sub(rb"\s+", b"", b), validate=False)
            j = dec.find(b"<?xml")
            if j >= 0:
                return dec[j:].decode("utf-8", errors="ignore")[:LIMITE_TESTO_ESTRATTO]
        except Exception:
            pass
        return ""


def prova_installa_pypdf(log):
    try:
        import pypdf  # noqa
        return True
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        pass
    log("pypdf non presente: provo a installarlo (pip install --user pypdf)...")
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "pypdf"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if r.returncode == 0:
            import importlib
            importlib.invalidate_caches()
            import site
            try:
                site.addsitedir(site.getusersitepackages())
            except Exception:
                pass
            import pypdf  # noqa
            log("pypdf installato.")
            return True
        log("installazione pypdf non riuscita: il testo dei PDF non sara' letto (si cerca solo nel nome).")
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as e:
        log("installazione pypdf non riuscita (%s): il testo dei PDF non sara' letto." % e)
    return False


# --------------------------------------------------------------------------------------
# Individuazione cartelle da esaminare
# --------------------------------------------------------------------------------------

def trova_drive_locale(profilo):
    """Cerca la cartella sincronizzata di Google Drive. Ritorna il percorso o None."""
    candidati = []
    if is_windows():
        sistema = (os.environ.get("SystemDrive") or "C:").upper()
        for lettera in string.ascii_uppercase:
            radice = lettera + ":\\"
            if lettera + ":" == sistema or not os.path.exists(radice):
                continue
            for nome in ("Il mio Drive", "My Drive"):
                p = os.path.join(radice, nome)
                if os.path.isdir(p):
                    candidati.append(p)
    for nome in ("Google Drive", "Il mio Drive", "My Drive"):
        p = os.path.join(profilo, nome)
        if os.path.isdir(p):
            candidati.append(p)
    try:
        for voce in os.listdir(profilo):
            if voce.lower().startswith("google drive") and os.path.isdir(os.path.join(profilo, voce)):
                candidati.append(os.path.join(profilo, voce))
    except OSError:
        pass
    # dentro "Google Drive" spesso c'e' "Il mio Drive"
    finali = []
    for c in candidati:
        for sub in ("Il mio Drive", "My Drive"):
            if os.path.isdir(os.path.join(c, sub)):
                c = os.path.join(c, sub)
                break
        if c not in finali:
            finali.append(c)
    return finali[0] if finali else None


def cartelle_profilo(profilo):
    nomi = ["Desktop", "Documents", "Documenti", "Downloads", "Download", "Pictures", "Immagini", "Videos", "Video",
            "Music", "Musica", "OneDrive", "Google Drive", "Il mio Drive", "My Drive", "WhatsApp", "Telegram Desktop",
            "Dropbox", "iCloudDrive", "Scansioni", "Scans", "Fatture", "Documenti scansionati"]
    trovate = []
    for n in nomi:
        p = os.path.join(profilo, n)
        if os.path.isdir(p) and p not in trovate:
            trovate.append(p)
    onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer") or os.environ.get("OneDriveCommercial")
    if onedrive and os.path.isdir(onedrive) and onedrive not in trovate:
        trovate.append(onedrive)
    try:
        for voce in os.listdir(profilo):
            p = os.path.join(profilo, voce)
            if os.path.isdir(p) and (voce.lower().startswith("onedrive") or voce.lower().startswith("google drive")) and p not in trovate:
                trovate.append(p)
    except OSError:
        pass
    return trovate


def dischi_esterni():
    if not is_windows():
        return []
    sistema = (os.environ.get("SystemDrive") or "C:").upper()
    esterni = []
    for lettera in string.ascii_uppercase:
        radice = lettera + ":\\"
        if lettera + ":" == sistema:
            continue
        if os.path.exists(radice):
            esterni.append(radice)
    return esterni


def rimuovi_annidate(cartelle):
    """Se una cartella e' contenuta in un'altra dell'elenco, tiene solo la piu' esterna."""
    norm = [os.path.normcase(os.path.abspath(c)) for c in cartelle]
    tenute = []
    for c, n in zip(cartelle, norm):
        if any(n != m and n.startswith(m.rstrip("\\/") + os.sep) for m in norm):
            continue
        if c not in tenute:
            tenute.append(c)
    return tenute


# --------------------------------------------------------------------------------------
# Proposta di riordino (Fase 2)
# --------------------------------------------------------------------------------------

FORNITORI_NOTI = ["unicomm", "guarnier", "worndle", "woerndle", "goodilia", "cortina bevande", "schinosa", "cuzziol",
                  "metro", "eviivo", "stripe", "nexi", "grenke", "findomestic", "santander", "compass", "volksbank",
                  "ford credit", "axa", "arca vita", "avepa", "binance", "coinbase", "revolut", "zmenu", "dacol",
                  "clickufficio", "rent for you", "aruba", "booking", "airbnb", "enel", "tim", "vodafone", "wind",
                  "fastweb", "iren", "hera", "edison", "eni", "a2a", "sorgenia"]
RX_FORNITORI = [(f, regex_da_parola(f)) for f in FORNITORI_NOTI]


def soggetto_per(nome_n, testo_n, parole_trovate):
    for f, rx in RX_FORNITORI:
        if rx.search(nome_n):
            return slug(f, 30)
    for p in parole_trovate:
        if p.startswith("nome:") and not p.startswith("nome:/"):
            return slug(p[5:], 30)
    for f, rx in RX_FORNITORI:
        if testo_n and rx.search(testo_n):
            return slug(f, 30)
    for p in parole_trovate:
        if p.startswith("testo:") and not p.startswith("testo:/"):
            return slug(p[6:], 30)
    return "laculla"


def contiene(nome_n, percorso_n, *parole):
    return any(p in nome_n or p in percorso_n for p in parole)


def proposta_cartella(rec, voce, parole_trovate):
    """Ritorna (cartella_proposta, motivazione, confidenza)."""
    nome_n = normalizza(rec["nome"])
    perc_n = normalizza(rec["percorso"])
    est = rec["estensione"]
    anno = rec["anno_doc"]
    if voce:
        dest = destinazione_voce(voce, nome_n, anno)
        return dest, "voce %d (%s)" % (voce, ", ".join(parole_trovate[:3])), "alta"
    c = lambda *p: contiene(nome_n, perc_n, *p)  # noqa: E731
    if c("cedolin", "busta paga", "bustapaga", "libro unico", "lul_"):
        return "03_PERSONALE/%d/cedolini" % anno, "nome/percorso: cedolini", "media"
    if c("assunzion", "unilav", "contratto di lavoro", "lettera di assunzione", "dimission"):
        return "03_PERSONALE/%d/assunzioni" % anno, "nome/percorso: assunzioni", "media"
    if c("haccp", "antincendio", "sicurezza", "dvr", "primo soccorso", "formazione"):
        return "03_PERSONALE/%d/sicurezza_haccp_antincendio" % anno, "nome/percorso: sicurezza/HACCP", "media"
    if c("carta vini", "carta dei vini", "lista vini", "wine list", "vini"):
        return "08_MENU_MARKETING/carta_vini", "nome/percorso: carta vini", "media"
    if c("menu", "menù", "carta ", "piatti"):
        return "08_MENU_MARKETING/menu", "nome/percorso: menu", "media"
    if c("canva"):
        return "08_MENU_MARKETING/canva", "nome/percorso: canva", "media"
    if c("listino", "listini", "price list"):
        return "06_FORNITORI/%s/listini" % soggetto_per(nome_n, "", []), "nome/percorso: listino", "media"
    if c("ordine", "ordini", "order", "preventivo", "offerta"):
        return "06_FORNITORI/%s/ordini" % soggetto_per(nome_n, "", []), "nome/percorso: ordine/preventivo", "bassa"
    if c("booking", "airbnb", "prenotazion", "ospit", "check in", "check-in", "checkin", "alloggiati", "istat", "guest"):
        return "07_OSPITI/%d" % anno, "nome/percorso: ospiti/prenotazioni", "media"
    if c("estratto conto", "estrattoconto", "movimenti", "lista movimenti", "e_c_", "conto corrente"):
        return "01_FISCALE/%d/01_estratti_conto" % anno, "nome/percorso: estratto conto", "media"
    if c("corrispettiv", "scontrin", "chiusura"):
        return "01_FISCALE/%d/06_corrispettivi" % anno, "nome/percorso: corrispettivi", "media"
    if c("f24", "imu", "tari", "iva ", "liquidazione iva", "bilancio", "commercialista", "dacol"):
        return "01_FISCALE/%d/09_commercialista" % anno, "nome/percorso: fiscale/commercialista", "media"
    if c("polizza", "assicurazion"):
        return "02_CONTRATTI/assicurazioni", "nome/percorso: assicurazione", "media"
    if c("bolletta", "bollette", "enel", "luce", "gas ", "energia", "telecom", "vodafone", "fastweb", "utenz", "acqua"):
        return "02_CONTRATTI/utenze", "nome/percorso: utenze", "media"
    if c("noleggio"):
        return "02_CONTRATTI/noleggi", "nome/percorso: noleggio", "media"
    if c("locazione", "affitto", "canone"):
        return "02_CONTRATTI/locazioni", "nome/percorso: locazione", "bassa"
    if c("contratto", "contract"):
        return "02_CONTRATTI/fornitori_servizi", "nome/percorso: contratto", "bassa"
    if est == ".xml" and c("fattur", "it0", "it1", "sdi"):
        return "01_FISCALE/%d/05_fatture_acquisto_xml" % anno, "xml fattura", "media"
    if c("fattura", "fatture", "invoice", "ricevuta", "receipt"):
        sogg = soggetto_per(nome_n, "", [])
        if sogg != "laculla":
            return "06_FORNITORI/%s" % sogg, "fattura fornitore noto", "media"
        return "01_FISCALE/%d/99_da_inviare_studio" % anno, "fattura/ricevuta da verificare", "bassa"
    if est in EST_IMMAGINI or est in EST_VIDEO:
        if c("rifugio", "valgrande"):
            return "04_STRUTTURE/rifugio", "foto/video rifugio", "media"
        if c("ristorante", "stube", "sala", "cucina"):
            return "04_STRUTTURE/ristorante", "foto/video ristorante", "media"
        if c("b&b", "bnb", "b_b", "camera", "camere", "stanza"):
            return "04_STRUTTURE/bnb", "foto/video B&B", "media"
        if c("attrezzatur", "inventario", "macchinari", "frigo", "cella"):
            return "05_ATTREZZATURE/foto_video/%s" % rec["data_doc"], "foto/video attrezzature", "media"
        if c("instagram", "social", "piatto", "food", "post", "marketing", "logo"):
            return "08_MENU_MARKETING/foto", "foto marketing", "bassa"
        if c("screenshot", "schermata", "whatsapp images", "whatsapp"):
            return "99_INBOX_DA_SMISTARE", "immagine screenshot/whatsapp", "bassa"
        return "99_INBOX_DA_SMISTARE", "immagine/video non classificabile dal nome", "bassa"
    if c("privat", "personale", "famiglia", "casa", "auto", "patente", "carta identita", "tessera sanitaria", "passaporto"):
        return "09_PRIVATO", "nome/percorso: privato", "bassa"
    return "99_INBOX_DA_SMISTARE", "nessuna regola applicabile", "bassa"


def destinazione_voce(voce, nome_n, anno):
    """Cartella di destinazione per la voce; le eccezioni guardano solo il NOME del file."""
    dest = DESTINAZIONE_VOCE[voce]
    for v, parole, alt in DESTINAZIONE_ECCEZIONI:
        if v == voce and any(p in nome_n for p in parole):
            dest = alt
            break
    return dest.replace("{anno}", str(anno))


def nome_proposto(rec, voce, parole_trovate):
    nome_n = normalizza(rec["nome"])
    stem, est = os.path.splitext(rec["nome"])
    if est.lower() == ".p7m" and stem.lower().endswith(".xml"):
        stem, est = stem[:-4], ".xml.p7m"
    sogg = soggetto_per(nome_n, "", parole_trovate)
    descr = slug(RE_DATA_ISO.sub(" ", RE_DATA_IT.sub(" ", stem)), 50)
    # toglie dalla descrizione le parole gia' usate come soggetto
    for tok in sogg.split("_"):
        if len(tok) >= 3:
            descr = re.sub(r"(^|_)" + re.escape(tok) + r"(?=_|$)", r"\1", descr)
    descr = re.sub(r"_+", "_", descr).strip("_")
    if not descr:
        descr = "documento"
    return "%s_%s_%s%s" % (rec["data_doc"], sogg, descr, est.lower())


# --------------------------------------------------------------------------------------
# Programma principale
# --------------------------------------------------------------------------------------

class Scansione:
    def __init__(self, args):
        self.args = args
        self.inizio = time.time()
        self.messaggi = []
        self.problemi = []
        self.cartelle_non_accessibili = []
        self.record = []
        self.copie = []
        self.per_hash = {}
        self.byte_totali = 0
        self.cartella_script = os.path.dirname(os.path.abspath(__file__))

    # ---- log ----
    def log(self, msg):
        riga = "[%s] %s" % (dt.datetime.now().strftime("%H:%M:%S"), msg)
        self.messaggi.append(riga)
        try:
            print(riga, flush=True)
        except Exception:
            print(riga.encode("ascii", "replace").decode("ascii"), flush=True)

    # ---- preparazione ----
    def prepara(self):
        a = self.args
        self.profilo = os.path.abspath(a.profilo or os.environ.get("USERPROFILE") or os.path.expanduser("~"))
        self.drive_locale = trova_drive_locale(self.profilo)
        if a.destinazione:
            self.destinazione = os.path.abspath(a.destinazione)
            self.modo_destinazione = "cartella indicata da riga di comando"
        elif self.drive_locale:
            self.destinazione = os.path.join(self.drive_locale, NOME_ARCHIVIO)
            self.modo_destinazione = "cartella Google Drive sincronizzata (%s)" % self.drive_locale
        else:
            doc = None
            for n in ("Documenti", "Documents"):
                p = os.path.join(self.profilo, n)
                if os.path.isdir(p):
                    doc = p
                    break
            if doc is None:
                doc = os.path.join(self.profilo, "Documents")
            self.destinazione = os.path.join(doc, NOME_ARCHIVIO)
            self.modo_destinazione = "NESSUNA cartella Google Drive locale trovata: le copie sono in Documenti (da caricare su Drive a mano)"
        self.cartella_scan = os.path.join(self.destinazione, CARTELLA_SCAN)

        if a.radici:
            radici = [os.path.abspath(r) for r in a.radici]
        else:
            radici = cartelle_profilo(self.profilo)
            if self.drive_locale and self.drive_locale not in radici:
                radici.append(self.drive_locale)
            if not a.no_esterni:
                for d in dischi_esterni():
                    if not any(os.path.normcase(r).startswith(os.path.normcase(d)) for r in radici):
                        radici.append(d)
            if not radici:
                radici = [self.profilo]
        self.radici = rimuovi_annidate(radici)

        cartelle_private = []
        for c in (self.cartella_script, self.cartella_scan,
                  os.path.join(self.profilo, "Documenti", NOME_ARCHIVIO, CARTELLA_SCAN),
                  os.path.join(self.profilo, "Documents", NOME_ARCHIVIO, CARTELLA_SCAN)):
            if os.path.normcase(os.path.abspath(c)) not in [os.path.normcase(os.path.abspath(x)) for x in cartelle_private]:
                cartelle_private.append(c)
        self.voci, self.privati = carica_voci(self.cartella_script, cartelle_private)
        usa_pypdf = not a.senza_pypdf and (a.no_install or True)
        if usa_pypdf and not a.no_install:
            usa_pypdf = prova_installa_pypdf(self.log)
        self.estrattore = Estrattore(usa_pypdf, a.max_contenuto_mb)
        self.log("Scansione PC La Culla v%s - modalita': %s" % (VERSIONE, "PROVA SENZA COPIE" if a.dry_run else ("SOLO INVENTARIO" if a.solo_inventario else "ricerca + copie + inventario")))
        self.log("Profilo utente: %s" % self.profilo)
        self.log("Destinazione archivio: %s  [%s]" % (self.destinazione, self.modo_destinazione))
        self.log("Cartelle esaminate: %s" % "; ".join(self.radici))
        self.log("Parole chiave private: %s" % (", ".join(self.privati) if self.privati else "nessun file parole_chiave_private.txt trovato"))
        self.log("Lettura testo PDF: %s" % ("si' (pypdf)" if self.estrattore.pypdf else "NO (solo nome file)"))
        self.escluse = set(CARTELLE_ESCLUSE) | {normalizza(x) for x in (a.escludi or [])}

    # ---- scansione ----
    def esamina_tutto(self):
        dest_norm = os.path.normcase(os.path.abspath(self.destinazione))
        n = 0
        for radice in self.radici:
            self.log("Esamino: %s" % radice)
            for cartella, sottocartelle, file in os.walk(radice, onerror=self._errore_walk):
                cart_norm = os.path.normcase(os.path.abspath(cartella))
                # non entrare nell'archivio di destinazione ne' in cartelle omonime (copie gia' fatte)
                sottocartelle[:] = [s for s in sottocartelle
                                    if normalizza(s) not in self.escluse
                                    and not s.startswith(".")
                                    and s != NOME_ARCHIVIO
                                    and os.path.normcase(os.path.join(cart_norm, s)) != dest_norm]
                sottocartelle.sort()
                for nome in file:
                    n += 1
                    if n % 500 == 0:
                        self.log("... %d file esaminati, %d nell'inventario" % (n, len(self.record)))
                    try:
                        self._esamina_file(cartella, nome)
                    except Exception as e:
                        self.problemi.append("errore su %s: %s" % (os.path.join(cartella, nome), e))
        self.log("Esame completato: %d file visti, %d nell'inventario." % (n, len(self.record)))

    def _errore_walk(self, err):
        p = getattr(err, "filename", None) or str(err)
        self.cartelle_non_accessibili.append(p)

    def _esamina_file(self, cartella, nome):
        if nome.lower() in NOMI_FILE_ESCLUSI:
            return
        percorso = os.path.join(cartella, nome)
        est = os.path.splitext(nome)[1].lower()
        if est in ESTENSIONI_ESCLUSE:
            return
        try:
            st = os.stat(percorso_lungo(percorso))
        except OSError as e:
            self.problemi.append("non accessibile: %s (%s)" % (percorso, e.strerror or e))
            return
        dim = st.st_size
        # file < 1 KB: tenuti solo se testuali o documenti (pdf/office/xml/p7m)
        if dim < 1024 and est not in EST_TESTO and est not in EST_OFFICE_ZIP and est not in EST_PDF and est not in EST_P7M:
            return
        if dim == 0:
            return
        mtime = dt.datetime.fromtimestamp(st.st_mtime)
        try:
            h = sha1_file(percorso, self.args.max_hash_mb * 1024 * 1024)
        except OSError as e:
            self.problemi.append("non leggibile: %s (%s)" % (percorso, e.strerror or e))
            return
        testo, nota = "", ""
        if est in EST_TESTO or est in EST_OFFICE_ZIP or est in EST_OFFICE_BIN or est in EST_PDF or est in EST_P7M or est == ".msg":
            testo, nota = self.estrattore.testo(percorso, est, dim)
            if nota and "PROTETTO" in nota:
                self.problemi.append("PDF protetto da password: %s" % percorso)
            elif nota and "password" in nota:
                self.problemi.append("file protetto da password: %s" % percorso)
        voce, secondarie, parole, punti = classifica(self.voci, nome, testo, est)
        data_doc, origine_data = data_da_nome(nome)
        anno_nome = anno_da_nome(nome)
        if data_doc is None and est in (".xml", ".p7m") and testo:
            data_doc, origine_data = data_da_xml(testo)
        if data_doc is None:
            data_doc, origine_data = mtime.date(), "modifica"
            anno = anno_nome or data_doc.year
        else:
            anno = data_doc.year
        if not (2015 <= anno <= 2035):
            anno = ANNO_RIFERIMENTO
        rec = {
            "percorso": percorso, "nome": nome, "estensione": est, "dimensione": dim,
            "data_modifica": mtime.strftime("%Y-%m-%d %H:%M:%S"), "sha1": h,
            "voce": voce or "", "voci_secondarie": " ".join(str(s) for s in secondarie),
            "parole_trovate": " | ".join(parole[:6]), "punteggio": punti, "nota": nota,
            "data_doc": data_doc.strftime("%Y-%m-%d"), "origine_data": origine_data, "anno_doc": anno,
        }
        self.record.append(rec)
        self.byte_totali += dim
        if h:
            self.per_hash.setdefault(h, []).append(percorso)

    # ---- copie (Fase 1) ----
    def copia_trovati(self):
        if self.args.solo_inventario:
            self.log("Solo inventario: nessuna copia.")
            return
        if not self.args.dry_run:
            for sub in SOTTOCARTELLE_FASE1:
                os.makedirs(percorso_lungo(os.path.join(self.destinazione, *sub.split("/"))), exist_ok=True)
        gia_copiati = {}
        for rec in self.record:
            if not rec["voce"]:
                continue
            voce = int(rec["voce"])
            dest_rel = destinazione_voce(voce, normalizza(rec["nome"]), rec["anno_doc"])
            cart_dest = os.path.join(self.destinazione, *dest_rel.split("/"))
            nome = rec["nome"]
            prefisso = rec["data_doc"] + "_"
            nuovo = nome if re.match(r"^20\d{2}-\d{2}-\d{2}_", nome) else prefisso + nome
            esito = ""
            if rec["sha1"] and rec["sha1"] in gia_copiati:
                esito = "saltato: contenuto identico gia' copiato (%s)" % gia_copiati[rec["sha1"]]
            else:
                dest_file = os.path.join(cart_dest, nuovo)
                stem, est = os.path.splitext(nuovo)
                k = 2
                while os.path.exists(percorso_lungo(dest_file)):
                    try:
                        if rec["sha1"] and sha1_file(dest_file, 0) == rec["sha1"]:
                            esito = "gia' presente a destinazione (identico)"
                            break
                    except OSError:
                        pass
                    dest_file = os.path.join(cart_dest, "%s_%d%s" % (stem, k, est))
                    k += 1
                if not esito:
                    if self.args.dry_run:
                        esito = "DRY-RUN: verrebbe copiato"
                    else:
                        try:
                            os.makedirs(percorso_lungo(cart_dest), exist_ok=True)
                            shutil.copy2(percorso_lungo(rec["percorso"]), percorso_lungo(dest_file))
                            esito = "copiato"
                        except OSError as e:
                            esito = "ERRORE copia: %s" % e
                            self.problemi.append("copia non riuscita: %s -> %s (%s)" % (rec["percorso"], dest_file, e))
                if rec["sha1"] and esito.startswith(("copiato", "DRY-RUN", "gia'")):
                    gia_copiati[rec["sha1"]] = dest_file
                nuovo = os.path.basename(dest_file)
            self.copie.append({"voce": voce, "origine": rec["percorso"], "destinazione": dest_rel + "/" + nuovo,
                               "esito": esito, "sha1": rec["sha1"], "dimensione": rec["dimensione"]})
        self.log("Copie: %d file candidati, %d copiati, %d saltati." % (
            len(self.copie), sum(1 for c in self.copie if c["esito"] == "copiato"),
            sum(1 for c in self.copie if c["esito"] != "copiato")))

    # ---- output (Fase 2) ----
    def scrivi_output(self):
        os.makedirs(percorso_lungo(self.cartella_scan), exist_ok=True)
        # inventario_pc.csv
        with open(os.path.join(self.cartella_scan, "inventario_pc.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["percorso", "nome", "estensione", "dimensione_byte", "data_modifica", "sha1", "voce", "voci_secondarie", "parole_trovate", "data_documento", "origine_data", "nota"])
            for r in sorted(self.record, key=lambda r: normalizza(r["percorso"])):
                w.writerow([r["percorso"], r["nome"], r["estensione"], r["dimensione"], r["data_modifica"], r["sha1"], r["voce"], r["voci_secondarie"], r["parole_trovate"], r["data_doc"], r["origine_data"], r["nota"]])
        # duplicati.csv
        self.gruppi_dup = {h: p for h, p in self.per_hash.items() if len(p) > 1}
        with open(os.path.join(self.cartella_scan, "duplicati.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["sha1", "numero_copie", "dimensione_byte", "percorso"])
            dim_per_hash = {r["sha1"]: r["dimensione"] for r in self.record if r["sha1"]}
            for h, percorsi in sorted(self.gruppi_dup.items(), key=lambda kv: -dim_per_hash.get(kv[0], 0) * len(kv[1])):
                for p in sorted(percorsi):
                    w.writerow([h, len(percorsi), dim_per_hash.get(h, ""), p])
        self.spazio_dup = sum(dim_per_hash.get(h, 0) * (len(p) - 1) for h, p in self.gruppi_dup.items())
        # proposta_riordino.csv
        self.n_proposte = 0
        with open(os.path.join(self.cartella_scan, "proposta_riordino.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["percorso_attuale", "nome_attuale", "cartella_proposta", "nome_proposto", "voce", "motivazione", "confidenza", "sha1", "duplicato"])
            for r in sorted(self.record, key=lambda r: normalizza(r["percorso"])):
                if r["estensione"] not in EST_LAVORO:
                    continue
                voce = int(r["voce"]) if r["voce"] else None
                parole = [p for p in r["parole_trovate"].split(" | ") if p]
                cart, motivo, conf = proposta_cartella(r, voce, parole)
                w.writerow([r["percorso"], r["nome"], NOME_ARCHIVIO + "/" + cart, nome_proposto(r, voce, parole), r["voce"], motivo, conf, r["sha1"], "si" if r["sha1"] in self.gruppi_dup else ""])
                self.n_proposte += 1
        # copie_eseguite.csv
        with open(os.path.join(self.cartella_scan, "copie_eseguite.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["voce", "origine", "destinazione_relativa", "esito", "sha1", "dimensione_byte"])
            for c in self.copie:
                w.writerow([c["voce"], c["origine"], c["destinazione"], c["esito"], c["sha1"], c["dimensione"]])
        # errori.log
        with open(os.path.join(self.cartella_scan, "errori.log"), "w", encoding="utf-8") as f:
            for p in self.cartelle_non_accessibili:
                f.write("cartella non accessibile: %s\n" % p)
            for p in self.problemi:
                f.write(p + "\n")
            for e in self.estrattore.errori:
                f.write("contenuto: %s\n" % e)
        self.scrivi_riepilogo()

    def scrivi_riepilogo(self):
        durata = time.time() - self.inizio
        righe = []
        righe.append("# RIEPILOGO scansione PC - La Culla")
        righe.append("")
        righe.append("Data: %s  -  durata %d min %d s  -  modalita': %s" % (
            dt.datetime.now().strftime("%Y-%m-%d %H:%M"), durata // 60, durata % 60,
            "PROVA SENZA COPIE (dry-run)" if self.args.dry_run else ("solo inventario" if self.args.solo_inventario else "ricerca + copie + inventario")))
        righe.append("")
        righe.append("Regola rispettata: nessun file spostato, rinominato o cancellato. Solo letture e copie.")
        righe.append("")
        righe.append("## Dove sono le copie")
        righe.append("")
        righe.append("- Cartella archivio: `%s`" % self.destinazione)
        righe.append("- Modalita': %s" % self.modo_destinazione)
        if not self.drive_locale and not self.args.destinazione:
            righe.append("- **ATTENZIONE**: non e' stata trovata una cartella Google Drive sincronizzata su questo PC. "
                         "La cartella `%s` va caricata su Google Drive a mano (trascinandola nella cartella `%s` del Drive)." % (NOME_ARCHIVIO, NOME_ARCHIVIO))
        righe.append("- Cartelle esaminate: %s" % "; ".join("`%s`" % r for r in self.radici))
        righe.append("")
        righe.append("## Le 10 voci della richiesta")
        righe.append("")
        for num in sorted(self.voci):
            v = self.voci[num]
            trovati = [r for r in self.record if r["voce"] == num]
            copie = [c for c in self.copie if c["voce"] == num]
            stato = "TROVATO (%d file)" % len(trovati) if trovati else "NON TROVATO"
            righe.append("### %d. %s - %s" % (num, v.nome, stato))
            righe.append("")
            if not trovati:
                righe.append("Nessun file con queste parole chiave nel nome o nel contenuto.")
                righe.append("")
                continue
            for r in sorted(trovati, key=lambda r: (-r["punteggio"], normalizza(r["nome"]))):
                c = next((c for c in copie if c["origine"] == r["percorso"]), None)
                dove = (" -> `%s` (%s)" % (c["destinazione"], c["esito"])) if c else ""
                righe.append("- `%s` (%s, %s; %s)%s" % (r["percorso"], fmt_dim(r["dimensione"]), r["data_modifica"][:10], r["parole_trovate"] or "-", dove))
            righe.append("")
        righe.append("## Numeri")
        righe.append("")
        righe.append("- File inventariati: %d (%s)" % (len(self.record), fmt_dim(self.byte_totali)))
        righe.append("- File con voce riconosciuta: %d" % sum(1 for r in self.record if r["voce"]))
        righe.append("- Copie eseguite: %d; saltate/duplicate: %d" % (
            sum(1 for c in self.copie if c["esito"] == "copiato"), sum(1 for c in self.copie if c["esito"] != "copiato")))
        righe.append("- Gruppi di duplicati (stesso SHA1 in piu' percorsi): %d, spazio recuperabile %s" % (len(self.gruppi_dup), fmt_dim(self.spazio_dup)))
        righe.append("- Righe nella proposta di riordino: %d (NON applicata: da approvare)" % self.n_proposte)
        righe.append("- Testo dei PDF letto: %s" % ("si'" if self.estrattore.pypdf else "NO (pypdf non disponibile: PDF cercati solo per nome)"))
        righe.append("")
        righe.append("File prodotti in `%s`: inventario_pc.csv, duplicati.csv, proposta_riordino.csv, copie_eseguite.csv, errori.log, RIEPILOGO.md" % self.cartella_scan)
        righe.append("")
        righe.append("## Problemi incontrati")
        righe.append("")
        if self.estrattore.pdf_protetti:
            righe.append("- PDF protetti da password (segnalati, non aperti):")
            for p in self.estrattore.pdf_protetti:
                righe.append("  - `%s`" % p)
        if self.cartelle_non_accessibili:
            righe.append("- Cartelle non accessibili (%d):" % len(self.cartelle_non_accessibili))
            for p in self.cartelle_non_accessibili[:50]:
                righe.append("  - `%s`" % p)
            if len(self.cartelle_non_accessibili) > 50:
                righe.append("  - ... (elenco completo in errori.log)")
        altri = [p for p in self.problemi if not p.startswith("PDF protetto")]
        if altri:
            righe.append("- Altri problemi (%d, dettaglio in errori.log):" % len(altri))
            for p in altri[:30]:
                righe.append("  - %s" % p)
        if not (self.estrattore.pdf_protetti or self.cartelle_non_accessibili or altri):
            righe.append("Nessuno.")
        righe.append("")
        testo = "\n".join(righe)
        with open(os.path.join(self.cartella_scan, "RIEPILOGO.md"), "w", encoding="utf-8") as f:
            f.write(testo)
        print("\n" + testo)

    def esegui(self):
        self.prepara()
        self.esamina_tutto()
        self.copia_trovati()
        self.scrivi_output()
        self.log("Fatto. Riepilogo in: %s" % os.path.join(self.cartella_scan, "RIEPILOGO.md"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scansione PC La Culla: ricerca documenti, copie in archivio, inventario. Solo lettura e copie.")
    ap.add_argument("--dry-run", action="store_true", help="non copia nulla; produce comunque inventario e riepilogo")
    ap.add_argument("--solo-inventario", action="store_true", help="salta la ricerca/copia (Fase 1), fa solo l'inventario (Fase 2)")
    ap.add_argument("--profilo", help="cartella profilo utente (default: %%USERPROFILE%%)")
    ap.add_argument("--radici", nargs="+", help="cartelle da esaminare (default: Desktop, Documenti, Download, Immagini, Video, OneDrive, Google Drive, dischi esterni)")
    ap.add_argument("--destinazione", help="cartella archivio di destinazione (default: Drive locale o Documenti)")
    ap.add_argument("--no-esterni", action="store_true", help="non esaminare gli altri dischi (D:, E:, ...)")
    ap.add_argument("--escludi", nargs="+", help="nomi di cartelle aggiuntive da saltare")
    ap.add_argument("--max-hash-mb", type=int, default=2048, help="non calcolare l'hash oltre questa dimensione (MB)")
    ap.add_argument("--max-contenuto-mb", type=int, default=30, help="non leggere il contenuto oltre questa dimensione (MB)")
    ap.add_argument("--senza-pypdf", action="store_true", help="non usare pypdf (test)")
    ap.add_argument("--no-install", action="store_true", help="non tentare pip install pypdf")
    args = ap.parse_args(argv)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    s = Scansione(args)
    try:
        s.esegui()
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.")
        return 130
    except Exception:
        traceback.print_exc()
        print("\nERRORE imprevisto. Nessun file originale e' stato toccato.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
