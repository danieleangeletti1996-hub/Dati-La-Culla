#!/usr/bin/env python3
"""
frames_from_video.py – Dai video del giro locale ai fotogrammi da leggere per l'inventario.

Per ogni video: estrae N fotogrammi al secondo (ffmpeg da imageio-ffmpeg), elimina i fotogrammi
quasi identici a quello precedente (hash percettivo), scrive un indice CSV e crea "tavole"
(griglie di 12 fotogrammi con il secondo stampato) per una lettura rapida.

Uso:
  python scripts/inventario/frames_from_video.py --in <cartella o file video> --out output/frames [--fps 1] [--threshold 6] [--max-width 1280]

Dipendenze: imageio-ffmpeg, pillow.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".3gp", ".webm", ".mts"}


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def ahash(img: Image.Image, size: int = 8) -> int:
    g = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    px = list(g.get_flattened_data()) if hasattr(g, "get_flattened_data") else list(g.getdata())
    avg = sum(px) / len(px)
    bits = 0
    for p in px:
        bits = (bits << 1) | (1 if p > avg else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def extract(video: Path, out_dir: Path, fps: float, max_width: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "f_%05d.jpg"
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
           "-vf", f"fps={fps},scale='min({max_width},iw)':-2", "-q:v", "3", str(pattern)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[errore] ffmpeg su {video.name}: {r.stderr.strip()[:300]}", file=sys.stderr)
        return []
    return sorted(out_dir.glob("f_*.jpg"))


def dedupe(frames: list[Path], threshold: int):
    """Ritorna lista di (frame, kept, hash, dup_of). Tiene il primo fotogramma di ogni gruppo simile."""
    result, last_kept, last_hash = [], None, None
    for f in frames:
        with Image.open(f) as im:
            h = ahash(im)
        if last_hash is not None and hamming(h, last_hash) <= threshold:
            result.append((f, False, h, last_kept.name))
            f.unlink()
        else:
            result.append((f, True, h, ""))
            last_kept, last_hash = f, h
    return result


def contact_sheets(kept: list[tuple[Path, float]], out_dir: Path, stem: str, cols: int = 4, rows: int = 3, thumb: int = 480):
    sheets = []
    per = cols * rows
    for i in range(0, len(kept), per):
        chunk = kept[i:i + per]
        th_h = None
        tiles = []
        for f, sec in chunk:
            with Image.open(f) as im:
                im = im.convert("RGB")
                ratio = thumb / im.width
                t = im.resize((thumb, max(1, int(im.height * ratio))))
            th_h = th_h or t.height
            d = ImageDraw.Draw(t)
            label = f"{stem}  {int(sec // 60):02d}:{int(sec % 60):02d}  ({f.name})"
            d.rectangle([0, 0, t.width, 22], fill=(0, 0, 0))
            d.text((6, 4), label, fill=(255, 255, 0))
            tiles.append(t)
        sheet = Image.new("RGB", (cols * thumb, rows * th_h), (30, 30, 30))
        for k, t in enumerate(tiles):
            sheet.paste(t, ((k % cols) * thumb, (k // cols) * th_h))
        p = out_dir / f"tavola_{stem}_{i // per + 1:02d}.jpg"
        sheet.save(p, quality=85)
        sheets.append(p)
    return sheets


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--threshold", type=int, default=6, help="distanza di Hamming max per considerare due fotogrammi uguali (0-64)")
    ap.add_argument("--max-width", type=int, default=1280)
    ap.add_argument("--no-sheets", action="store_true")
    args = ap.parse_args(argv)

    src, out = Path(args.src), Path(args.out)
    videos = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.suffix.lower() in VIDEO_EXT)
    if not videos:
        print(f"[errore] nessun video in {src}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    index = out / "index.csv"
    total_kept = total = 0
    with index.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["video", "fotogramma", "secondo", "tenuto", "hash", "duplicato_di"])
        for v in videos:
            stem = v.stem
            frames = extract(v, out / stem, args.fps, args.max_width)
            res = dedupe(frames, args.threshold)
            kept = []
            for n, (f, k, h, dup) in enumerate(res, start=1):
                sec = (n - 1) / args.fps
                w.writerow([v.name, f.name if k else "", f"{sec:.1f}", "SI" if k else "", f"{h:016x}", dup])
                if k:
                    kept.append((f, sec))
            total += len(res)
            total_kept += len(kept)
            sheets = [] if args.no_sheets else contact_sheets(kept, out / stem, stem)
            print(f"{v.name}: {len(res)} fotogrammi, {len(kept)} tenuti, {len(sheets)} tavole")
    print(f"totale: {total} fotogrammi, {total_kept} tenuti; indice: {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
