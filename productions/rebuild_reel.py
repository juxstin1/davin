"""Rebuild a DASH CLIP/BROLL reel from per-clip 540p proxies, exactly the way
the review package made it (ffmpeg concat demuxer, stream copy).

    uv run python productions/rebuild_reel.py "<drop>/Day 05/MA129-Music Therapy" CLIP \
        --proxies "<Downloads>/drive-download-.../Shoot-Day Transcripts/05 Day" \
        --out "<Downloads>/Making Arrangements (rebuilt reels)/Day 05/MA129-Music Therapy"

Reads <KIND>_REEL_concat.txt + <KIND>_REEL_manifest.tsv from the story folder,
finds each proxy by file name under --proxies (recursively), and refuses to
build unless every proxy exists and its duration matches its manifest row
(+/-5ms): the transcript timecodes, and every cut made from them, assume those
exact durations. Writes <stem>_<KIND>_REEL.mp4, named like the package's own
reels so Resolve relinks by file name.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path


def probe(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("kind", choices=["CLIP", "BROLL"])
    ap.add_argument("--proxies", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="output directory")
    ap.add_argument("--name", help="reel file name (default: derived from folder)")
    ap.add_argument("--skip-leading", type=int, default=0,
                    help="drop the first N clips (missing proxies); reel time = original - their durations")
    args = ap.parse_args()

    concat = args.folder / f"{args.kind}_REEL_concat.txt"
    wanted = [line.split("'")[1] for line in concat.read_text(encoding="utf-8").splitlines() if line.startswith("file ")]
    with (args.folder / f"{args.kind}_REEL_manifest.tsv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert len(rows) == len(wanted), (len(rows), len(wanted))
    offset = sum(float(r["duration_seconds"]) for r in rows[: args.skip_leading])
    rows, wanted = rows[args.skip_leading :], wanted[args.skip_leading :]

    index = {}
    for p in args.proxies.rglob("*_proxy_540p.mp4"):
        index.setdefault(p.name, []).append(p)

    files, problems = [], []
    for row, src in zip(rows, wanted):
        name = Path(src).name
        hits = index.get(name, [])
        if not hits:
            problems.append(f"missing {name}")
            continue
        got, want = probe(hits[0]), float(row["duration_seconds"])
        if abs(got - want) > 0.005:
            problems.append(f"{name}: {got:.3f}s vs manifest {want:.3f}s")
            continue
        files.append(hits[0])
    if problems:
        print(f"{len(problems)} problem(s) - not building:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(2)

    stem = args.name or {
        # match the package's own reel names so Resolve relinks by file name
        "MA129-Music Therapy": "MA129-Music Therapy",
    }.get(args.folder.name, args.folder.name)
    args.out.mkdir(parents=True, exist_ok=True)
    suffix = f"_from-{rows[0]['filename'].split('-CAM ')[-1]}" if args.skip_leading else ""
    dst = args.out / f"{stem}_{args.kind}_REEL{suffix}.mp4"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        for f in files:
            fh.write("file '" + str(f).replace("'", "'\\''") + "'\n")
        listing = fh.name
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing,
         # v+a only: the proxies' tmcd data track won't stream-copy into mp4
         "-map", "0:v", "-map", "0:a", "-c", "copy", str(dst)],
        check=True,
    )
    total = sum(float(r["duration_seconds"]) for r in rows)
    got = probe(dst)
    print(f"{dst}\n  {len(files)} proxies, reel {got:.3f}s vs manifest {total:.3f}s ({(got - total) * 1000:+.0f}ms)")


if __name__ == "__main__":
    main()
