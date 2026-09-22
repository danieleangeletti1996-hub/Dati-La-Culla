#!/usr/bin/env python3
"""
scan_pc.py – Inventario del computer per il riordino dell'archivio La Culla (solo lettura, nessuna modifica).
Pensato per la sessione Claude locale (Windows/macOS/Linux). Solo libreria standard; pypdf opzionale per i PDF.

Uso:
  python scan_pc.py --out "<cartella di output>" [--roots "C:/Users/xxx" "D:/"] [--copy-to "<cartella ARCHIVIO>"]
        [--no-content] [--max-hash-mb 200]

Produce in --out:
  inventario_pc.csv      un rigo per file (percorso, nome, estensione, dimensione, data, sha1, voce trovata)
  duplicati.csv          file identici (stesso sha1) in più percorsi
  trovati_per_voce.md    per ognuna delle voci fiscali: elenco dei file trovati
  proposta_riordino.csv  per ogni file di lavoro: cartella di destinazione proposta (da approvare, non applicata)
  RIEPILOGO.md           conteggi e problemi
Con --copy-to copia (non sposta) i file trovati per le voci fiscali nella struttura ARCHIVIO, con prefisso data.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import os
import re
import shutil
import sys
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {"appdata", "library", ".git", "node_modules", "__pycache__", "program files", "program files (x86)",
             "windows", "$recycle.bin", ".cache", ".npm", ".venv", "venv", "site-packages", "applications",
             "system volume information", ".trash", ".local", "snap", "proc", "sys", "dev", "onedrivetemp",
             ".gradle", ".m2", "anaconda3", "miniconda3", ".vscode", ".idea", "steam", "steamapps"}
TEXT_EXT = {".txt", ".csv", ".xml", ".eml", ".md", ".json", ".html", ".htm", ".p7m"}
DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ods", ".odt", ".ppt", ".pptx", ".txt", ".csv", ".xml", ".p7m",
           ".eml", ".msg", ".zip", ".rtf", ".md", ".json"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff", ".gif"}
VID_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".webm"}

# voce -> (parole chiave, cartella ARCHIVIO di destinazione)
# Le parole chiave combaciano come parole intere (minuscolo, senza accenti); "*" finale = anche i prefissi.
VOCI = {
    "01_crypto": (["binance", "coinbase", "revolut", "crypto*", "cripto*", "bitcoin", "btc", "ethereum", "wallet", "imposta di bollo"],
                  "01_FISCALE/{anno}/07_crypto"),
    "02_finanziamenti": (["findomestic", "ford credit", "santander", "compass", "piano di ammortamento", "piano rate",
                          "documento di sintesi", "finanziament*", "mutuo", "chirografari*", "20221876625345", "000401618",
                          "17659937", "volksbank"], "01_FISCALE/{anno}/02_finanziamenti"),
    "03_noleggi": (["grenke", "rent foryou", "rent for you", "rentforyou", "noleggi*", "verbale di consegna", "clickufficio",
                    "20250131012", "12545692"], "02_CONTRATTI/noleggi"),
    "04_stripe_pos": (["stripe", "payout*", "riepilogo saldo", "nexi", "pos", "commissioni pos"], "01_FISCALE/{anno}/03_pos_stripe_nexi"),
    "05_eviivo": (["eviivo", "ev00*", "ire004252", "evl023556"], "01_FISCALE/{anno}/04_eviivo"),
    "06_fatture_xml": (["fatturapa", "fattura elettronica", "fatture ricevute", "fatture passive", "it01241890258*",
                        "unicomm", "guarnier", "woerndle", "wörndle", "goodilia", "cortina bevande", "schinosa", "cuzziol"],
                       "01_FISCALE/{anno}/05_fatture_acquisto_xml"),
    "07_isa_redditi": (["isa", "eg44u", "dati compilati", "scheda redditi", "redditi 20*", "modello unico", "dichiarazione dei redditi",
                        "modello redditi", "irpef", "f24"], "01_FISCALE/{anno}/08_isa_redditi"),
    "08_contratti_beni": (["affitto azienda", "affitto d'azienda", "affitto di azienda", "valgrande", "moie", "de martin topranin",
                           "rogito", "notaio", "inventario", "elenco beni", "attrezzatur*", "cespiti", "prezzo moie", "libro cespiti"],
                          "02_CONTRATTI/affitto_azienda_valgrande"),
    "09_assicurazioni_contributi": (["arca vita", "1172122", "axa", "401618", "polizza", "avepa", "contributo", "cella frigorifera"],
                                    "02_CONTRATTI/assicurazioni"),
    "10_corrispettivi_magazzino": (["zmenu", "report giornaliero", "chiusura", "corrispettivi", "rimanenze", "giacenze", "magazzino",
                                    "totale venduto", "venduto 20*"], "01_FISCALE/{anno}/06_corrispettivi"),
}
FISCAL_VOCI = set(VOCI)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower())


def _kw_regex(kw: str):
    kw = norm(kw)
    if kw.endswith("*"):
        return re.compile(r"(?<![a-z0-9])" + re.escape(kw[:-1]))
    return re.compile(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])")


VOCI_RX = {voce: [_kw_regex(k) for k in kws] for voce, (kws, _) in VOCI.items()}


def sha1_of(p: Path, limit_bytes: int) -> str:
    try:
        if p.stat().st_size > limit_bytes:
            return ""
        h = hashlib.sha1()
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def read_text(p: Path, ext: str, max_bytes: int = 5_000_000) -> str:
    try:
        if p.stat().st_size > max_bytes:
            return ""
        if ext in TEXT_EXT:
            return p.read_text(encoding="utf-8", errors="ignore")
        if ext in (".docx", ".xlsx", ".pptx", ".odt", ".ods"):
            with zipfile.ZipFile(p) as z:
                names = [n for n in z.namelist() if n.endswith(".xml") and ("document" in n or "sharedStrings" in n or "content" in n or "slide" in n)]
                return " ".join(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore")) for n in names[:20])
        if ext == ".pdf":
            try:
                from pypdf import PdfReader  # opzionale
            except Exception:
                return ""
            r = PdfReader(str(p))
            return " ".join((pg.extract_text() or "") for pg in r.pages[:5])
    except Exception:
        return ""
    return ""


def year_of(name: str, mtime: dt.datetime) -> str:
    m = re.search(r"(20[12]\d)", name)
    return m.group(1) if m else str(mtime.year)


def match_voci(text: str) -> list[str]:
    return [voce for voce, rxs in VOCI_RX.items() if any(rx.search(text) for rx in rxs)]


def proposed_folder(voci: list[str], ext: str, name: str, mtime: dt.datetime) -> str:
    anno = year_of(name, mtime)
    if voci:
        return VOCI[voci[0]][1].format(anno=anno)
    if ext in IMG_EXT or ext in VID_EXT:
        return f"05_ATTREZZATURE/foto_video/{mtime.strftime('%Y-%m')}" if "img" not in name and "whatsapp" not in name else "99_INBOX_DA_SMISTARE"
    if ext in DOC_EXT:
        return "99_INBOX_DA_SMISTARE"
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roots", nargs="*", default=[str(Path.home())])
    ap.add_argument("--out", required=True)
    ap.add_argument("--copy-to", help="cartella ARCHIVIO in cui copiare i file delle voci fiscali (solo copie)")
    ap.add_argument("--no-content", action="store_true", help="non leggere il contenuto dei file (solo nomi)")
    ap.add_argument("--max-hash-mb", type=int, default=200)
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="cartelle da non scandire (es. la cartella Google Drive sincronizzata e l'ARCHIVIO stesso)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    limit = args.max_hash_mb * 1024 * 1024
    excludes = [out.resolve()] + [Path(e).resolve() for e in args.exclude if Path(e).exists()]
    if args.copy_to and Path(args.copy_to).exists():
        excludes.append(Path(args.copy_to).resolve())
    rows, by_hash, found, problems = [], defaultdict(list), defaultdict(list), []
    n_dirs = 0
    for root in args.roots:
        rp = Path(root)
        if not rp.exists():
            problems.append(f"radice inesistente: {root}")
            continue
        for dirpath, dirnames, filenames in os.walk(rp, onerror=lambda e: problems.append(f"non accessibile: {e.filename}")):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith(".")]
            dp = Path(dirpath).resolve()
            if any(dp == ex or ex in dp.parents for ex in excludes):
                dirnames[:] = []
                continue
            n_dirs += 1
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    st = p.stat()
                except OSError:
                    problems.append(f"stat fallita: {p}")
                    continue
                ext = p.suffix.lower()
                if st.st_size < 1024 and ext not in TEXT_EXT:
                    continue
                mtime = dt.datetime.fromtimestamp(st.st_mtime)
                text = norm(fn + " " + str(p.parent.name))
                if not args.no_content and ext in DOC_EXT and st.st_size <= 5_000_000:
                    text += " " + norm(read_text(p, ext)[:200_000])
                voci = match_voci(text)
                digest = sha1_of(p, limit) if (ext in DOC_EXT or ext in IMG_EXT or ext in VID_EXT) else ""
                row = [str(p), fn, ext, st.st_size, mtime.isoformat(timespec="seconds"), digest, "|".join(voci),
                       proposed_folder(voci, ext, fn.lower(), mtime)]
                rows.append(row)
                if digest:
                    by_hash[digest].append(str(p))
                for v in voci:
                    found[v].append(row)

    with (out / "inventario_pc.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["percorso", "nome", "estensione", "dimensione", "modificato", "sha1", "voci", "cartella_proposta"])
        w.writerows(rows)
    with (out / "duplicati.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["sha1", "n_copie", "percorsi"])
        for h, ps in by_hash.items():
            if len(ps) > 1:
                w.writerow([h, len(ps), " | ".join(ps)])
    with (out / "proposta_riordino.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["percorso_attuale", "nome_proposto", "cartella_proposta", "voci", "approvato (SI/NO)"])
        for r in rows:
            if r[7]:
                mt = dt.datetime.fromisoformat(r[4])
                nome = r[1] if re.match(r"^20\d\d-\d\d-\d\d_", r[1]) else f"{mt:%Y-%m-%d}_{r[1]}"
                w.writerow([r[0], nome, r[7], r[6], ""])
    with (out / "trovati_per_voce.md").open("w", encoding="utf-8") as fh:
        fh.write("# File trovati per voce fiscale\n\n")
        for v in VOCI:
            fh.write(f"## {v} ({len(found[v])} file)\n\n")
            for r in sorted(found[v], key=lambda r: r[4], reverse=True)[:200]:
                fh.write(f"- {r[4][:10]} · {r[1]} · {r[3]//1024} KB · `{r[0]}`\n")
            fh.write("\n")

    copied = 0
    if args.copy_to:
        dest_root = Path(args.copy_to)
        seen_hashes = set()
        for r in rows:
            if not r[6]:
                continue
            if r[5] and r[5] in seen_hashes:  # stesso contenuto già copiato (duplicato)
                continue
            v = r[6].split("|")[0]  # una sola destinazione: la prima voce trovata
            mt = dt.datetime.fromisoformat(r[4])
            target = dest_root / VOCI[v][1].format(anno=year_of(r[1].lower(), mt))
            target.mkdir(parents=True, exist_ok=True)
            nome = r[1] if re.match(r"^20\d\d-\d\d-\d\d_", r[1]) else f"{mt:%Y-%m-%d}_{r[1]}"
            dst = target / nome
            if dst.exists():
                continue
            try:
                shutil.copy2(r[0], dst)
                copied += 1
                if r[5]:
                    seen_hashes.add(r[5])
            except OSError as e:
                problems.append(f"copia fallita {r[0]}: {e}")

    dups = sum(1 for ps in by_hash.values() if len(ps) > 1)
    size_gb = sum(r[3] for r in rows) / 1e9
    with (out / "RIEPILOGO.md").open("w", encoding="utf-8") as fh:
        fh.write(f"# Riepilogo scansione PC – {dt.datetime.now():%Y-%m-%d %H:%M}\n\n")
        fh.write(f"- Radici: {', '.join(args.roots)}\n- Cartelle visitate: {n_dirs}\n- File inventariati: {len(rows)} ({size_gb:.1f} GB)\n")
        fh.write(f"- Gruppi di duplicati: {dups}\n- File copiati in ARCHIVIO: {copied}\n\n## Voci fiscali\n\n")
        for v in VOCI:
            fh.write(f"- {v}: {'trovati ' + str(len(found[v])) + ' file' if found[v] else 'NON TROVATO'}\n")
        if problems:
            fh.write("\n## Problemi\n\n" + "\n".join(f"- {p}" for p in problems[:200]) + "\n")
    print(f"file: {len(rows)}; duplicati: {dups}; copiati: {copied}; problemi: {len(problems)}; output: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
