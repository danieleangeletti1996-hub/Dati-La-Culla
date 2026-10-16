#!/usr/bin/env python3
"""
avvia_scansione.py – Avvio "a un clic" della scansione del PC per l'archivio La Culla.

Trova da solo la cartella di Google Drive per desktop e, dentro, "LA CULLA – ARCHIVIO"; poi esegue scan_pc.py
(nella stessa cartella di questo file) con:
  radici  = profilo utente + altri dischi fissi/esterni (mai la cartella Google Drive, che è già in cloud)
  output  = ARCHIVIO/00_scan  (inventario_pc.csv, duplicati.csv, proposta_riordino.csv, trovati_per_voce.md, RIEPILOGO.md)
  copie   = ARCHIVIO/...      (i documenti fiscali trovati, copiati, mai spostati)
Se Google Drive per desktop non c'è, usa Documenti\\LA CULLA – ARCHIVIO e lo dice chiaramente: quella cartella va poi
caricata su Drive a mano.

Uso: doppio clic su AVVIA_SCANSIONE.cmd (Windows) oppure
     python avvia_scansione.py [--archivio "<cartella ARCHIVIO>"] [--solo-nomi] [--no-open]
Solo libreria standard. Non modifica, non sposta e non cancella alcun file del PC.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import string
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # nessun __pycache__ dentro la cartella Drive
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ARCHIVIO_NAMES = ("LA CULLA – ARCHIVIO", "LA CULLA - ARCHIVIO", "LA CULLA — ARCHIVIO", "LA CULLA_ARCHIVIO")
DRIVE_SUBDIRS = ("Il mio Drive", "My Drive")
DRIVE_MARKERS = DRIVE_SUBDIRS + ("Drive condivisi", "Shared drives")


def _win_drive_type(root: Path) -> int:
    """3 = fisso, 2 = rimovibile, 4 = di rete, 5 = CD, 6 = RAM, 0/1 = sconosciuto (solo Windows)."""
    if sys.platform != "win32":
        return 3
    try:
        import ctypes

        return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(str(root)))
    except Exception:
        return 0


def drive_letters() -> list[Path]:
    if sys.platform != "win32":
        return []
    return [Path(f"{L}:/") for L in string.ascii_uppercase if Path(f"{L}:/").exists()]


def is_google_drive_mount(root: Path) -> bool:
    try:
        return any((root / m).is_dir() for m in DRIVE_MARKERS)
    except OSError:
        return False


def drive_candidates(home: Path) -> list[Path]:
    """Possibili cartelle "Il mio Drive" di Google Drive per desktop, in ordine di probabilità."""
    cands: list[Path] = []
    for root in drive_letters():  # Windows: Drive per desktop montato come lettera (di solito G:)
        for sub in DRIVE_SUBDIRS:
            cands.append(root / sub)
    for base in (home / "Google Drive", home, home / "GoogleDrive"):  # modalità "mirror" dentro il profilo
        for sub in DRIVE_SUBDIRS:
            cands.append(base / sub)
        cands.append(base)
    cloud = home / "Library" / "CloudStorage"  # macOS
    if cloud.is_dir():
        for d in sorted(cloud.glob("GoogleDrive-*")):
            for sub in DRIVE_SUBDIRS:
                cands.append(d / sub)
    return cands


def find_archivio(home: Path, explicit: str | None = None) -> tuple[Path, Path | None, str]:
    """Ritorna (cartella ARCHIVIO, radice Google Drive da escludere dalla scansione, come è stata trovata)."""
    if explicit:
        p = Path(explicit).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        mount = next((c for c in drive_candidates(home) if c in p.resolve().parents), None)
        return p, mount, "indicata a riga di comando"
    for cand in drive_candidates(home):
        if not cand.is_dir():
            continue
        for name in ARCHIVIO_NAMES:
            if (cand / name).is_dir():
                return cand / name, cand, f"Google Drive: {cand}"
    for base in (home, home / "Documenti", home / "Documents", home / "Desktop", home / "OneDrive"):
        for name in ARCHIVIO_NAMES:
            if (base / name).is_dir():
                return base / name, None, f"cartella locale: {base}"
    docs = next((d for d in (home / "Documenti", home / "Documents") if d.is_dir()), home)
    fallback = docs / ARCHIVIO_NAMES[0]
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback, None, "NON TROVATA su Google Drive: creata in " + str(fallback)


def scan_roots(home: Path, exclude_mount: Path | None) -> list[Path]:
    roots = [home]
    for root in drive_letters():
        if exclude_mount and exclude_mount.resolve().drive.upper() == root.drive.upper():
            continue
        if root.drive.upper() == home.drive.upper():
            continue  # il disco di sistema è coperto dal profilo utente
        if is_google_drive_mount(root) or _win_drive_type(root) not in (2, 3):
            continue  # Google Drive, dischi di rete, CD: no
        roots.append(root)
    return roots


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archivio", help="cartella LA CULLA – ARCHIVIO (se non indicata viene cercata in Google Drive)")
    ap.add_argument("--solo-nomi", action="store_true", help="non leggere il contenuto dei file (più veloce)")
    ap.add_argument("--no-open", action="store_true", help="non aprire RIEPILOGO.md alla fine")
    ap.add_argument("--home", help=argparse.SUPPRESS)  # solo per i test
    ap.add_argument("--radici", nargs="*", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    home = Path(args.home).expanduser() if args.home else Path.home()
    archivio, mount, how = find_archivio(home, args.archivio)
    roots = [Path(r) for r in args.radici] if args.radici else scan_roots(home, mount)
    out = archivio / "00_scan"
    out.mkdir(parents=True, exist_ok=True)
    excludes = [str(p) for p in (mount, archivio) if p]

    log = out / "AVVIO.log"
    started = dt.datetime.now()
    lines = [f"[{started:%Y-%m-%d %H:%M:%S}] avvio scansione",
             f"  profilo utente : {home}",
             f"  ARCHIVIO       : {archivio}  ({how})",
             f"  radici scandite: {', '.join(map(str, roots))}",
             f"  escluse        : {', '.join(excludes) or '-'}",
             f"  modalità       : {'solo nomi' if args.solo_nomi else 'nomi + contenuto'}"]
    print("\n".join(lines))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    import scan_pc  # nella stessa cartella

    cmd = ["--roots", *map(str, roots), "--out", str(out), "--copy-to", str(archivio), "--exclude", *excludes]
    if args.solo_nomi:
        cmd.append("--no-content")
    rc = scan_pc.main(cmd)

    ended = dt.datetime.now()
    tail = [f"[{ended:%Y-%m-%d %H:%M:%S}] fine (durata {ended - started}), codice {rc}",
            f"  risultati in: {out}",
            "  " + ("Google Drive li sincronizza da solo: la sessione cloud può leggerli." if mount
                    else "ATTENZIONE: cartella non su Google Drive. Caricare la cartella ARCHIVIO su Drive (LA CULLA – ARCHIVIO).")]
    print("\n".join(tail))
    with log.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(tail) + "\n")
    riepilogo = out / "RIEPILOGO.md"
    if not args.no_open and sys.platform == "win32" and riepilogo.exists():
        try:
            os.startfile(str(riepilogo))  # type: ignore[attr-defined]
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
